#!/usr/bin/env python3

import sys
from pathlib import Path
import pandas as pd

STATUS_CSV = Path('final_pipeline/evaluation/five_site_validation/five_site_pipeline_status.csv')
OUT_DIR = Path('final_pipeline/evaluation/five_site_validation/inspection')
SUMMARY_CSV = OUT_DIR / 'five_site_recommendation_summary.csv'
SAMPLES_CSV = OUT_DIR / 'five_site_inspection_samples.csv'


def clean(value):
    if pd.isna(value):
        return ''
    return str(value).strip()


def to_bool(value):
    if isinstance(value, bool):
        return value
    return clean(value).lower() in {'true', '1', 'yes', 'y'}


def first_value(row, candidates):
    for col in candidates:
        if col in row.index:
            value = clean(row.get(col, ''))
            if value:
                return value
    return ''


def find_component_rows(df, component):
    if component == 'link':
        if 'link_v4_processed' in df.columns:
            return df[df['link_v4_processed'].apply(to_bool)].copy()

        link_rules = {'empty_link_text', 'link-name', 'generic_link_text'}
        mask = pd.Series(False, index=df.index)
        for col in ['custom_issue', 'axe_rule', 'primary_rule', 'rule']:
            if col in df.columns:
                mask |= df[col].apply(clean).isin(link_rules)
        return df[mask].copy()

    if component == 'vlm':
        if 'vlm_processed' in df.columns:
            return df[df['vlm_processed'].apply(to_bool)].copy()
        if 'vlm_status' in df.columns:
            return df[df['vlm_status'].apply(clean).ne('')].copy()
        return df.iloc[0:0].copy()

    raise ValueError(component)


def link_specific(row):
    name = first_value(row, [
        'link_v4_suggested_accessible_name',
        'link_v4_suggested_name',
        'link_suggested_accessible_name',
        'link_suggested_name',
    ])
    html = first_value(row, ['link_v4_suggested_html', 'link_suggested_html'])
    return bool(name or html)


def link_abstention(row):
    confidence = first_value(row, ['link_v4_confidence', 'link_confidence']).lower()
    decision = first_value(row, [
        'link_v4_decision_code',
        'link_decision_code',
        'link_v4_action',
    ]).lower()
    suggestion = first_value(row, [
        'link_v4_suggested_accessible_name',
        'link_v4_suggested_name',
        'link_suggested_accessible_name',
        'link_suggested_name',
    ])
    if suggestion:
        return False
    return (
        confidence == 'low'
        or 'insufficient' in decision
        or 'manual' in decision
        or 'unclear' in decision
        or 'abstain' in decision
    )


def vlm_specific(row):
    suggested_alt = first_value(row, ['vlm_suggested_alt', 'suggested_alt'])
    action = first_value(row, ['vlm_recommended_action', 'recommended_action']).lower()
    decorative_action = any(token in action for token in [
        'empty alt', 'alt=""', 'decorative', 'set_empty', 'replace_with_empty'
    ])
    return bool(suggested_alt or decorative_action)


def pick_samples(df, component, n=3):
    if df.empty:
        return []
    work = df.copy()
    if component == 'link':
        conf_cols = ['link_v4_confidence', 'link_confidence']
        decision_cols = ['link_v4_decision_code', 'link_decision_code']
    else:
        conf_cols = ['vlm_confidence', 'confidence']
        decision_cols = ['vlm_image_role', 'image_role']

    work['_confidence'] = work.apply(lambda r: first_value(r, conf_cols), axis=1)
    work['_decision'] = work.apply(lambda r: first_value(r, decision_cols), axis=1)

    selected = []
    seen = set()
    for idx, row in work.iterrows():
        key = (clean(row['_confidence']).lower(), clean(row['_decision']).lower())
        if key in seen:
            continue
        selected.append((idx, row))
        seen.add(key)
        if len(selected) >= n:
            break

    if len(selected) < n:
        selected_indices = {idx for idx, _ in selected}
        for idx, row in work.iterrows():
            if idx in selected_indices:
                continue
            selected.append((idx, row))
            if len(selected) >= n:
                break
    return selected


def sample_record(site, row, component):
    common = {
        'site_id': site['site_id'],
        'website_name': site['website_name'],
        'category': site['category'],
        'component': component,
        'unified_id': first_value(row, ['unified_id', 'finding_id', 'id']),
        'issue': first_value(row, ['custom_issue', 'axe_rule', 'primary_rule', 'rule']),
        'selector': first_value(row, ['preferred_selector', 'selector']),
        'html': first_value(row, ['preferred_html', 'affected_html', 'html']),
        'context': first_value(row, ['context', 'nearby_context', 'context_text', 'contextual_evidence']),
    }

    if component == 'Link V4':
        common.update({
            'decision_or_role': first_value(row, ['link_v4_decision_code', 'link_decision_code']),
            'confidence': first_value(row, ['link_v4_confidence', 'link_confidence']),
            'suggestion': first_value(row, [
                'link_v4_suggested_accessible_name',
                'link_v4_suggested_name',
                'link_suggested_accessible_name',
                'link_suggested_name',
            ]),
            'recommended_action': first_value(row, [
                'link_v4_recommended_action', 'link_v4_action', 'link_recommended_action'
            ]),
            'suggested_html': first_value(row, ['link_v4_suggested_html', 'link_suggested_html']),
        })
    else:
        common.update({
            'decision_or_role': first_value(row, ['vlm_image_role', 'image_role']),
            'confidence': first_value(row, ['vlm_confidence', 'confidence']),
            'suggestion': first_value(row, ['vlm_suggested_alt', 'suggested_alt']),
            'recommended_action': first_value(row, ['vlm_recommended_action', 'recommended_action']),
            'suggested_html': first_value(row, ['vlm_suggested_html']),
        })
    return common


def main():
    if not STATUS_CSV.exists():
        print('ERROR:')
        print(f'Status CSV not found: {STATUS_CSV.resolve()}')
        print('Run this script from ~/bd-web-accessibility-ai')
        sys.exit(2)

    status = pd.read_csv(STATUS_CSV)
    required = {'site_id', 'website_name', 'category', 'recommendation_csv'}
    missing = required - set(status.columns)
    if missing:
        print('ERROR:')
        print('Status CSV is missing columns:', ', '.join(sorted(missing)))
        sys.exit(2)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    summary_rows = []
    sample_rows = []

    print('=' * 96)
    print('FIVE-SITE RECOMMENDATION INSPECTION')
    print('=' * 96)

    for _, srow in status.iterrows():
        site = {
            'site_id': clean(srow.get('site_id', '')),
            'website_name': clean(srow.get('website_name', '')),
            'category': clean(srow.get('category', '')),
        }
        rec_path = Path(clean(srow.get('recommendation_csv', '')))

        print()
        print('-' * 96)
        print(f"{site['site_id']} | {site['website_name']} | {site['category']}")
        print('-' * 96)

        if not rec_path.exists():
            print(f'Recommendation CSV not found: {rec_path}')
            continue

        df = pd.read_csv(rec_path)
        link_df = find_component_rows(df, 'link')
        vlm_df = find_component_rows(df, 'vlm')

        link_specific_count = int(link_df.apply(link_specific, axis=1).sum()) if not link_df.empty else 0
        link_abstention_count = int(link_df.apply(link_abstention, axis=1).sum()) if not link_df.empty else 0
        vlm_specific_count = int(vlm_df.apply(vlm_specific, axis=1).sum()) if not vlm_df.empty else 0

        vlm_manual_count = 0
        for col in ['vlm_manual_review_required', 'vlm_visual_review_required']:
            if col in vlm_df.columns:
                vlm_manual_count = max(vlm_manual_count, int(vlm_df[col].apply(to_bool).sum()))

        print(f'Total final findings:          {len(df)}')
        print(f'Link V4 processed:             {len(link_df)}')
        print(f'Link V4 specific suggestions:  {link_specific_count}')
        print(f'Link V4 abstention/manual:     {link_abstention_count}')
        print(f'VLM processed:                 {len(vlm_df)}')
        print(f'VLM specific treatments:       {vlm_specific_count}')
        print(f'VLM manual/visual review:      {vlm_manual_count}')

        summary_rows.append({
            'site_id': site['site_id'],
            'website_name': site['website_name'],
            'category': site['category'],
            'total_final_findings': len(df),
            'link_v4_processed': len(link_df),
            'link_v4_specific_suggestions': link_specific_count,
            'link_v4_abstention_or_manual': link_abstention_count,
            'vlm_processed': len(vlm_df),
            'vlm_specific_treatments': vlm_specific_count,
            'vlm_manual_or_visual_review': vlm_manual_count,
            'recommendation_csv': str(rec_path),
        })

        for _, row in pick_samples(link_df, 'link', n=3):
            sample_rows.append(sample_record(site, row, 'Link V4'))
        for _, row in pick_samples(vlm_df, 'vlm', n=3):
            sample_rows.append(sample_record(site, row, 'VLM'))

    summary_df = pd.DataFrame(summary_rows)
    samples_df = pd.DataFrame(sample_rows)

    summary_df.to_csv(SUMMARY_CSV, index=False, encoding='utf-8-sig')
    samples_df.to_csv(SAMPLES_CSV, index=False, encoding='utf-8-sig')

    print()
    print('=' * 96)
    print('CROSS-SITE TOTALS')
    print('=' * 96)

    if not summary_df.empty:
        print('Total findings:                ', int(summary_df['total_final_findings'].sum()))
        print('Link V4 processed:             ', int(summary_df['link_v4_processed'].sum()))
        print('Link V4 specific suggestions:  ', int(summary_df['link_v4_specific_suggestions'].sum()))
        print('Link V4 abstention/manual:     ', int(summary_df['link_v4_abstention_or_manual'].sum()))
        print('VLM processed:                 ', int(summary_df['vlm_processed'].sum()))
        print('VLM specific treatments:       ', int(summary_df['vlm_specific_treatments'].sum()))

    print()
    print('Files created:')
    print(SUMMARY_CSV.resolve())
    print(SAMPLES_CSV.resolve())
    print()
    print('Next: inspect the sample CSV first. Do not calculate accuracy yet.')


if __name__ == '__main__':
    main()
