import unittest
import numpy as np
from pipeline.core.preprocessing import smooth_power_db
from pipeline.core.change_detection import detect, otsu_threshold
from pipeline.core.ml_model import spatial_split, scores


class RadarTests(unittest.TestCase):
    def test_filter_linear_power_not_log(self):
        power=np.ones((9,9),dtype='float32');power[4,4]=100
        expected=10*np.log10((100+24)/25)
        self.assertAlmostEqual(float(smooth_power_db(power)[4,4]),expected,places=5)

    def test_invalid_pixels_stay_missing(self):
        power=np.ones((9,9),dtype='float32');power[4,4]=np.nan;power[4,5]=0
        result=smooth_power_db(power)
        self.assertTrue(np.isnan(result[4,4]));self.assertTrue(np.isnan(result[4,5]))
        self.assertAlmostEqual(float(result[3,3]),0)
        self.assertTrue(np.isnan(result[0,0]))

    def test_new_water_excludes_existing_and_small_patches(self):
        before=np.zeros((12,12));after=before.copy();hv=before.copy();ahv=before.copy()
        after[2:7,2:7]=-15;ahv[2:7,2:7]=-2
        before[9,9]=-20;after[9,9]=-22;ahv[9,9]=-2
        after[0,0]=-15;ahv[0,0]=-2
        mask,_=detect(before,after,hv,ahv,-10,min_pixels=25)
        self.assertEqual(int(mask.sum()),25)

    def test_otsu_between_distinct_modes(self):
        threshold=otsu_threshold(np.r_[np.full(100,-20),np.full(100,-5)])
        self.assertTrue(-20<threshold<-5)

    def test_spatial_guard_and_repeat_date_assignment(self):
        x=np.array([760050.,760500.,760500.]);y=np.array([1820500.]*3)
        split=spatial_split(x,y)
        self.assertEqual(split[0],-1)
        self.assertEqual(split[1],split[2])
        self.assertGreaterEqual(split[1],0)

    def test_absent_event_metrics_are_undefined(self):
        result=scores(np.zeros(10),np.zeros(10))
        self.assertIsNone(result['precision']);self.assertIsNone(result['recall'])
        self.assertIsNone(result['iou']);self.assertEqual(result['tn'],10)


if __name__=='__main__':unittest.main()
