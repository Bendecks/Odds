import sys
sys.path.insert(0, 'scripts')
import identity_coverage_analysis as mod


def row(market, exact=False, books=3):
    r={'market':market,'books':books}
    if exact:
        r.update({'bet365_verified':True,'bet365_event_id':'e1','event_match_method':'exact'})
    return r


def test_build_counts_missing_exact_by_market():
    report=mod.build([row('h2h',True,5),row('h2h'),row('totals'),row('totals')])
    assert report['candidate_rows']==4
    assert report['exact_rows']==1
    assert report['missing_exact_rows']==3
    by={x['market']:x for x in report['markets']}
    assert by['h2h']['exact_rate']==0.5
    assert by['totals']['missing_exact_rows']==2


def test_reference_ready_requires_three_books():
    report=mod.build([row('h2h',True,2),row('h2h',True,3)])
    h2h=report['markets'][0]
    assert h2h['exact_rows']==2
    assert h2h['reference_ready_rows']==1
    assert h2h['reference_ready_rate']==0.5


def test_fuzzy_identity_never_counts_as_exact():
    r=row('h2h')
    r.update({'bet365_verified':True,'bet365_event_id':'e1','event_match_method':'resolver'})
    report=mod.build([r])
    assert report['exact_rows']==0
    assert report['missing_exact_rows']==1
