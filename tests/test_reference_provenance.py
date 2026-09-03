import sys, unittest
sys.path.insert(0,'scripts')
import odds_api_io_reference as reference

class ReferenceProvenanceTests(unittest.TestCase):
    def test_unibet_provenance_is_explicit(self):
        source=reference.reference_provenance()
        self.assertEqual(source['transport_provider_id'],'odds-api.io')
        self.assertEqual(source['economic_source_id'],'unibet')
        self.assertEqual(source['evidence_family'],'market_price')
        self.assertTrue(source['model_or_feed_version'])

    def test_same_bookmaker_through_two_transports_counts_once(self):
        sources=[
            {'transport_provider_id':'transport-a','economic_source_id':'unibet'},
            {'transport_provider_id':'transport-b','economic_source_id':'Unibet'},
        ]
        self.assertEqual(reference.unique_economic_source_count(sources),1)

    def test_independent_economic_sources_count_separately(self):
        sources=[
            {'transport_provider_id':'transport-a','economic_source_id':'unibet'},
            {'transport_provider_id':'transport-a','economic_source_id':'pinnacle'},
        ]
        self.assertEqual(reference.unique_economic_source_count(sources),2)

    def test_missing_source_id_never_inflates_depth(self):
        sources=[{'transport_provider_id':'a'},{'transport_provider_id':'b','economic_source_id':''}]
        self.assertEqual(reference.unique_economic_source_count(sources),0)

if __name__=='__main__': unittest.main()
