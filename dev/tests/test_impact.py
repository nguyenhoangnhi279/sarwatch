"""Analytical checks use independent synthetic geometry; no fabricated results."""
import tempfile
from pathlib import Path
import unittest

try:
    import numpy as np
    import rasterio
    from rasterio.transform import from_origin
    from shapely.geometry import box, mapping
    from pipeline.core.impact_analysis import population_exposure, infrastructure_exposure, order_for_review
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE, 'Run with the GIS processing environment')
class ImpactTests(unittest.TestCase):
    def feature(self, ident, geom, **properties):
        return {'type':'Feature','geometry':mapping(geom),'properties':{'id':ident,'area_m2':geom.area,**properties}}

    def test_population_conservation_and_nodata(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'pop.tif'
            with rasterio.open(p,'w',driver='GTiff',height=1,width=2,count=1,dtype='float32',crs='EPSG:4326',transform=from_origin(107.5,16.5,.001,.001),nodata=-99999) as ds:
                ds.write(np.array([[100,-99999]],dtype='float32'),1)
            features=[self.feature(1,box(107.5,16.499,107.5005,16.5)),self.feature(2,box(107.5005,16.499,107.501,16.5)),self.feature(3,box(107.501,16.499,107.502,16.5))]
            r,_=population_exposure(features,p)
            self.assertAlmostEqual(r['1']['population_estimate']+r['2']['population_estimate'],100,places=3)
            self.assertIsNone(r['3']['population_estimate'])
            self.assertEqual(r['3']['population_status'],'no_valid_cells')

    def test_actual_line_overlap_not_whole_road(self):
        from shapely.geometry import LineString
        candidate=self.feature(1,box(107.5,16.499,107.501,16.5))
        roads=[{'type':'Feature','geometry':mapping(LineString([(107.499,16.4995),(107.502,16.4995)])),'properties':{'osm_id':'way/1','name':'Fixture','kind':'residential'}}]
        r,lines,_,total=infrastructure_exposure([candidate],roads,[],box(107.49,16.49,107.51,16.51))
        self.assertGreater(total,100);self.assertLess(total,110)
        self.assertEqual(r['1']['road_object_count'],1)
        self.assertEqual(len(lines['features']),1)

    def test_transparent_ordering(self):
        a=self.feature(1,box(0,0,1,1),population_estimate=1000,road_length_m=10,facility_count=0)
        b=self.feature(2,box(0,0,1,1),population_estimate=10,road_length_m=0,facility_count=1)
        c=self.feature(3,box(0,0,1,1),population_estimate=None,road_length_m=100,facility_count=0)
        r=order_for_review([c,a,b])
        self.assertEqual([x['properties']['id'] for x in r],[2,1,3])
        self.assertEqual(r[0]['properties']['review_basis'],'essential_facility')


if __name__=='__main__':unittest.main()
