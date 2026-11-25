import json
import tempfile
import unittest
from pathlib import Path
import pandas as pd
from src.datasets import (
    DATASET_PROVENANCE,
    add_dataset,
    clean_coordinates,
    dataset_provenance,
    detect_coordinate_pairs,
    list_datasets,
    load_dataset,
    remove_dataset,
)

class TestDatasets(unittest.TestCase):
    def test_invalid_coordinates_removed(self):
        data = pd.DataFrame({'lat':[40.7, 0, 91, None], 'lon':[-73.9, 0, 20, -70]})
        self.assertEqual(len(clean_coordinates(data, 'lat','lon')), 1)

    def test_food_file(self):
        self.assertIn('Restaurant_latitude', load_dataset('Food delivery records').columns)

    def test_grubhub_file(self):
        self.assertIn('searched_lat', load_dataset('Grubhub restaurant listings').columns)

    def test_builtin_provenance_is_documented(self):
        for name in DATASET_PROVENANCE:
            info = dataset_provenance(name)
            self.assertTrue(info['source_url'].startswith('http'), msg=name)
            self.assertNotIn('not yet verified', info['source'].lower(), msg=name)
            self.assertNotIn('not yet verified', info['license'].lower(), msg=name)
            self.assertTrue(info.get('approx_records', 0) > 0, msg=name)
        names = [item['name'] for item in list_datasets()]
        self.assertEqual(names[0], 'Grubhub restaurant listings')

    def test_detects_known_coordinate_names(self):
        food = detect_coordinate_pairs([
            'Restaurant_latitude', 'Restaurant_longitude',
            'Delivery_location_latitude', 'Delivery_location_longitude',
        ])
        self.assertEqual(food, [
            ('Restaurant_latitude', 'Restaurant_longitude'),
            ('Delivery_location_latitude', 'Delivery_location_longitude'),
        ])
        grubhub = detect_coordinate_pairs(['latitude', 'longitude', 'searched_lat', 'searched_lng'])
        self.assertEqual(grubhub, [('latitude', 'longitude'), ('searched_lat', 'searched_lng')])

    def test_add_load_and_remove_user_file(self):
        with tempfile.TemporaryDirectory() as folder:
            content = 'stop,latitude,longitude\nA,40.7,-74.0\nB,40.8,-74.1\n'
            added = add_dataset('Campus stops', 'campus stops.csv', content, user_dir=folder)
            self.assertEqual(added['rows'], 2)
            self.assertEqual(added['coordinates'], [('latitude', 'longitude')])
            names = [item['name'] for item in list_datasets(folder)]
            self.assertIn('Campus stops', names)
            loaded = load_dataset('Campus stops', user_dir=folder)
            self.assertEqual(list(loaded['stop']), ['A', 'B'])
            remove_dataset('Campus stops', user_dir=folder)
            self.assertNotIn('Campus stops', [item['name'] for item in list_datasets(folder)])
            self.assertFalse(Path(added['path']).exists())

    def test_dropped_file_is_listed_without_catalog(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'extra.json'
            path.write_text(json.dumps([{'lat': 1, 'lon': 2}, {'lat': 3, 'lon': 4}]), encoding='utf-8')
            match = next(item for item in list_datasets(folder) if item['name'] == 'extra')
            self.assertFalse(match['builtin'])
            self.assertEqual(match['coordinates'], [('lat', 'lon')])
            self.assertEqual(len(load_dataset('extra', user_dir=folder)), 2)

    def test_rejects_unsafe_or_duplicate_files(self):
        with tempfile.TemporaryDirectory() as folder:
            add_dataset('First', 'stops.csv', 'lat,lon\n1,2\n', user_dir=folder)
            with self.assertRaises(ValueError):
                add_dataset('First', 'other.csv', 'lat,lon\n1,2\n', user_dir=folder)
            with self.assertRaises(ValueError):
                add_dataset('Notes', 'notes.txt', 'hello', user_dir=folder)
            added = add_dataset('Traversal', '../outside.csv', 'lat,lon\n1,2\n', user_dir=folder)
            self.assertEqual(Path(added['path']).parent, Path(folder))
            self.assertEqual(Path(added['path']).name, 'outside.csv')
            with self.assertRaises(ValueError):
                remove_dataset('Food delivery records', user_dir=folder)

    def test_manual_coordinate_columns(self):
        with tempfile.TemporaryDirectory() as folder:
            content = 'pickup_y,pickup_x\n40.1,-73.2\n'
            added = add_dataset('Pickups', 'pickups.csv', content, [('pickup_y', 'pickup_x')], user_dir=folder)
            self.assertEqual(added['coordinates'], [('pickup_y', 'pickup_x')])

if __name__ == '__main__':
    unittest.main()
