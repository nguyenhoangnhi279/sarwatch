import unittest
try:
    import numpy as np
    from pipeline.reference import optical_masks
    AVAILABLE=True
except ImportError:
    AVAILABLE=False


@unittest.skipUnless(AVAILABLE,'Run with the GIS processing environment')
class OpticalReferenceTests(unittest.TestCase):
    def test_water_transition_is_not_existing_water(self):
        before=np.array([[4,6,5,3]],dtype='uint8')
        after=np.array([[6,6,5,6]],dtype='uint8')
        valid,new,existing=optical_masks(before,after,0)
        np.testing.assert_array_equal(valid,[[True,True,True,False]])
        np.testing.assert_array_equal(new,[[True,False,False,False]])
        np.testing.assert_array_equal(existing,[[False,True,False,False]])

    def test_cloud_edge_buffer_excludes_uncertain_neighbours(self):
        before=np.full((9,9),4,dtype='uint8');after=before.copy();after[4,4]=9
        valid,_,_=optical_masks(before,after,1)
        self.assertFalse(valid[4,4]);self.assertFalse(valid[4,3]);self.assertTrue(valid[2,2])


if __name__=='__main__':unittest.main()
