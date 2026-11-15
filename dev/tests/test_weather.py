import unittest
from app.server.weather import accumulation, validate_forecast, forecast_url
from app.server.verification import scores


class WeatherTests(unittest.TestCase):
    def fixture(self):
        return {'hourly_units': {'precipitation': 'mm'}, 'hourly': {
            'time': [3600*i for i in range(1, 16)], 'precipitation': [2.0]*15}}

    def test_partial_hours(self):
        self.assertEqual(accumulation(self.fixture(), 1800, 5)['mm'], 10)
        self.assertEqual(accumulation(self.fixture(), 1800, 12)['mm'], 24)

    def test_missing_is_not_zero(self):
        d = self.fixture()
        d['hourly']['precipitation'][2] = None
        self.assertIsNone(accumulation(d, 1800, 5)['mm'])
        self.assertIsNone(accumulation(d, 14*3600, 5)['mm'])

    def test_preceding_hour(self):
        d = self.fixture()
        d['hourly']['precipitation'][:2] = [4, 8]
        self.assertEqual(accumulation(d, 1800, 1)['mm'], 6)

    def test_validation(self):
        validate_forecast(self.fixture())
        d = self.fixture(); d['hourly']['time'][2] += 1
        with self.assertRaises(ValueError): validate_forecast(d)
        d = self.fixture(); d['hourly']['precipitation'][2] = float('nan')
        with self.assertRaises(ValueError): validate_forecast(d)

    def test_scores(self):
        s = scores([(10,10), (10,0), (0,10), (0,0)], 5)
        self.assertEqual(s['MAE_mm'], 5)
        self.assertAlmostEqual(s['RMSE_mm'], 50**.5)
        self.assertEqual(s['POD'], .5)
        self.assertEqual(s['FAR'], .5)
        self.assertAlmostEqual(s['CSI'], 1/3)

    def test_no_events_undefined(self):
        s = scores([(0,0)], 5)
        self.assertIsNone(s['POD']); self.assertIsNone(s['FAR']); self.assertIsNone(s['CSI'])
        with self.assertRaises(ValueError): scores([], 5)

    def test_provider(self):
        self.assertIn('models=ecmwf_ifs', forecast_url())


if __name__ == '__main__': unittest.main()
