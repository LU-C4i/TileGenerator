# AUTOGENERATED! DO NOT EDIT! File to edit: tile_generator.ipynb (unless otherwise specified).

__all__ = ['Map', 'TileGenerator', 'create_rectange_polygon', 'get_quad_grid', 'generate_train_valid_test']

# Cell
from mapbox import StaticStyle
from mapbox import Static
from mapbox import Geocoder
import os
import numpy as np
from PIL import Image as im
import io
import math
import yaml
import pandas as pd
import random
from dataclasses import dataclass
from pathlib import Path

# Cell
@dataclass
class Map():
    map_type:str
    user:str
    key:str
    file_name:str

# Cell
class TileGenerator:
    '''Use this class to access Mapbox API and generate tiles'''

    def __init__(self, settings_file = 'mapbox_settings.yaml',
                 parent_directory = '.',
                 train = 'train', valid = 'valid'):
        '''Initialise a tile generator with a yaml settings file.
        Set the parent directory path and names of training an validation folders'''
        with open(settings_file) as f:
            try:
                self.data = yaml.load(f, Loader=yaml.FullLoader)
                self.token = self.data['MAPBOX_ACCESS_TOKEN']
                self.data_types = self._map_data(self.data['ids'])
            except:
                print('Check the settings file path:', settings_file)

        self._initialize_services()
        self.parent_directory = parent_directory
        self.train = train
        self.valid = valid
        self.image_size = 0

    def _initialize_services(self):
        '''Set the mapbox access token for both the StaticStyle API and Static API sessions'''
        self.service_style = StaticStyle(self.token)
        self.service_static = Static(self.token)
        self.service_geocoder = Geocoder()
        os.environ['MAPBOX_ACCESS_TOKEN'] = self.token
        self.service_style.session.params['access_token'] == os.environ['MAPBOX_ACCESS_TOKEN']
        self.service_static.session.params['access_token'] == os.environ['MAPBOX_ACCESS_TOKEN']
        self.service_geocoder.session.params['access_token'] == os.environ['MAPBOX_ACCESS_TOKEN']

    def _map_data(self, ids:dict) -> dict:
        data_type = {}
        for id, info in self.data['ids'].items():
            data_type[id] = Map(info['type'], info['user'], info['key'], info['file_name'])
        return data_type

    def get_styleid_response(self, lon:float, lat:float, zoom:int, data_type:str, features = None, width=512, height=512):
        '''Retrieve the raster data for a given style available from Mapbox either from already created styles or
        from user created ones in Mapbox Studio. Longitude, latitude, zoom and data type are required.
        Additional features can be added to this raster by providing a json object for the features argument.'''
        if self.data_types[data_type].map_type != 'style':
            return 'Not the right data type. Must be a style type for the StaticStyle API'
        response = self.service_style.image(username=self.data_types[data_type].user, style_id=self.data_types[data_type].key,
                                            features = features, lon=lon, lat=lat, zoom=zoom, width=width, height=height)
        return response.content

    def get_mapid_response(self, lon:float, lat:float, zoom:int, data_type:str, features=None, width=512, height=512):
        '''Retrieve the raster data for a given map id with longitude, latitude, zoom and data type. Additional features
        can be added to this raster by providing a json object for the features argument.'''
        if self.data_types[data_type].map_type != 'map':
            return 'Not the right data type. Must be a map type for the Static API'
        mapid  = f'{self.data_types[data_type].user}.{self.data_types[data_type].key}'
        response = self.service_static.image(mapid, lon, lat, z=zoom, features=features,width=width, height=height)
        return response.content

    def get_response(self, lon, lat, zoom, data_type, features=None, width=512, height=512):
        '''Response depending on data type.'''
        if self.data_types[data_type].map_type == 'style':
            return self.get_styleid_response(lon, lat, zoom, data_type, features, width=width, height=height)
        elif self.data_types[data_type].map_type == 'map':
            return self.get_mapid_response(lon, lat, zoom, data_type, features, width=width, height=height)
        else: 'Not a recognised data type.'

    def view_style_tile(self, lon, lat, zoom, data_type, additional_features = None):
        '''View tile image from Mapbox style definition'''
        xr = self.get_styleid_response(lon, lat, zoom, data_type, additional_features)
        img = im.open(io.BytesIO(xr))
        if self.image_size != 0: img = img.crop((0,0,self.image_size,self.image_size))
        img = img.convert('RGB')
        return img

    def view_map_tile(self, lat, lon, zoom, data_type, additional_features = None):
        '''View tile image based on Mapbox Map API'''
        xr = self.get_mapid_response(lat, lon, zoom, data_type, features = additional_features)
        img = im.open(io.BytesIO(xr))
        if self.image_size != 0: img = img.crop((0,0,self.image_size,self.image_size))
        img = img.convert('RGB')
        return img

    def file_exist(self,file_name:str):
        '''Create directories if they do not exist'''
        path = Path(f'{file_name}/')
        if not path.exists():
            path.mkdir()

    def check_and_create_folder(self, file_name):
        p = Path(file_name)
        pth = Path()
        for i in p.parts:
            pth = pth.joinpath(i+'/')
            self.file_exist(pth)

    def get_tile_set(self, lon:float, lat:float, zoom:int, processors:dict, file_list:list,
                     additional_features:dict = None, add_features:list = None, file:str='train', compress_level = 3, width=512, height=512):
        for data_type, func in processors.items():
            feature = None
            if data_type in add_features: feature = additional_features
            self.check_and_create_folder(f'{self.parent_directory}/{self.data_types[data_type].file_name}/{file}')
            if not self.file_exists(file_list, self.data_types[data_type].file_name, file, lon, lat, zoom):
                xr = self.get_response(lon, lat, zoom, data_type, feature, width=width, height= height)
                img = im.open(io.BytesIO(xr))
                if self.image_size != 0: img = img.crop((0,0,self.image_size,self.image_size))
                img = img.convert('RGB')
                func(img)
                img.save(f'{self.parent_directory}/{self.data_types[data_type].file_name}/{file}/{lon},{lat},{zoom}.png','PNG',compress_level = compress_level)

    def get_existing_files(self, file_name:str, file:str = 'train')->list:
        '''Find all existing files inside file (defalut is train) and retrn list'''
        existing_files = [f'{file_name}/{file}/{o.name}' for o in os.scandir(f'{self.parent_directory}/{file_name}/{file}')]
        return existing_files

    def file_exists(self, file_list:list, file_name:str, file:str, lon:float, lat:float, zoom:int)->bool:
        '''Check if file exists'''
        file_path = f'{file_name}/{file}/{lon},{lat},{zoom}.png'
        return True if file_path in file_list else False

    def generate_tile_set(self, top_left_lon:float, top_left_lat:float, bottom_right_lon:float, bottom_right_lat:float,
                          zoom:int, processors:dict, add_features:list, valid_percentage = 10, image_crop = 0, g:dict = None, max_imgs:int=1000, compress_level = 3,
                         width=512, height=512):
        '''Method used to generate a set of tiles inside an area defined by the upper left corner and lower right corner'''
        per = int(100 / valid_percentage)
        total_imgs = 0
        train_existing_files = []
        valid_existing_files = []
        if self.image_size == image_crop:
            for f,_ in processors.items():
                train_existing_files.extend(self.get_existing_files(self.data_types[f].file_name, self.train))
                if self.valid: valid_existing_files.extend(self.get_existing_files(self.data_types[f].file_name, self.valid))
        else:
            self.image_size = image_crop
        tl_x, tl_y, _ = self.lat_lon_to_x_y(top_left_lat, top_left_lon, zoom)
        br_x, br_y, _ = self.lat_lon_to_x_y(bottom_right_lat, bottom_right_lon, zoom)
        tot = int((abs(br_x - tl_x) + 1) * (abs(tl_y - br_y) + 1))
        for j in range( int(abs(tl_y - br_y)) + 1):
            for i in range( int(abs(br_x - tl_x)) + 1):
                lat, lon = self.x_y_lat_lon(tl_x - i*0.71, tl_y - j, zoom)
                if total_imgs % per == 0 and self.valid != None:
                    self.get_tile_set(lat, lon, zoom, processors, valid_existing_files, additional_features = g, add_features = add_features, file = self.valid, compress_level=compress_level, width=width, height=height)
                else:
                    self.get_tile_set(lat, lon, zoom, processors, train_existing_files, additional_features = g, add_features = add_features, file = self.train, compress_level=compress_level, width=width, height=height)
                total_imgs += 1
                if total_imgs == max_imgs:
                    return
                tenper = int(0.1*tot) if int(0.1*tot) > 1 else tot
                if int(total_imgs % tenper) == 0:
                    per = int(100*total_imgs/tot)
                    print(f'{per}%')

    def generate_tiles_around_lat_lon(self, lat:float, lon:float, zoom:int, lat_lon_list:list, processors:dict,
                                      add_features:list, feature_scale = 0.0002, tile_num:int = 1,
                                      valid_percentage = 10, image_crop = 0, g:dict = None,
                                      max_imgs:int=1000, compress_level = 3, width=512, height=512):
        '''generate a set of tiles arounf a latitude and longitude'''
        per = int(100 / valid_percentage)
        total_imgs = 0
        lat_lon_pairs = []
        total_tiles = (2*tile_num + 1)
        tl_x, tl_y, _ = self.lat_lon_to_x_y(lat, lon, zoom)
        train_existing_files = []
        valid_existing_files = []
        if self.image_size == image_crop:
            for f,_ in processors.items():
                train_existing_files.extend(self.get_existing_files(self.data_types[f].file_name, self.train))
                if self.valid: valid_existing_files.extend(self.get_existing_files(self.data_types[f].file_name, self.valid))
        else:
            self.image_size = image_crop
        for x in range(3):
            for y in range(3):
                lat_lon_pairs.append((tl_x + 0.25 * (x - 1),tl_y + 0.25 * (y - 1)))
        for ll in lat_lon_pairs:
            for j in range(total_tiles):
                for i in range(total_tiles):
                    lat, lon = self.x_y_lat_lon(ll[0] + tile_num - i, ll[1] + tile_num - j, zoom)
                    lls, ftrs = self.find_nn_ll(lat, lon, lat_lon_list, zoom, feature_scale)
                    if ftrs['type'] == 'None': ftrs = None
                    if total_imgs % per == 0 and self.valid != None:
                        self.get_tile_set(lls[1], lls[0], zoom, processors, valid_existing_files, additional_features = ftrs, add_features = add_features, file = self.valid, compress_level=compress_level, width=width, height=height)
                    else:
                        self.get_tile_set(lls[1], lls[0], zoom, processors, train_existing_files, additional_features = ftrs, add_features = add_features, file = self.train, compress_level=compress_level, width=width, height=height)
                    total_imgs += 1

    def find_nn_ll(self, lati, long, ll_list, zoom, scale:float):
        '''Find other latitudes and longitudes in the same tile. There is a limit on the number of neighbours
        to be found as there is a character limit in the Mapbox query (see the counter variable in this method).'''
        lati = lati
        long = long
        size_func = lambda x: math.log(x + 1)*scale
        x, y, _ = self.lat_lon_to_x_y(lati, long, zoom)
        minx = x - 0.5
        maxx = x + 0.5
        miny = y - 0.5
        maxy = y + 0.5
        nn_list = []
        counter = 0
        #counter is needed to restrict the number of rectangles created as there is a character limit
        #for the string when submitting a query to Mapbox
        for o in ll_list:
            if self.filter_area(o, minx, maxx, miny, maxy, zoom) and counter < 6:
                nn_list.append(self.create_rectangle_polygon(o, size_func))
                counter += 1
        features = ' '.join(map(str,nn_list))
        if len(nn_list) > 0:
            nns = {'type': 'FeatureCollection','features': nn_list}
        else:
            nns = {'type': 'None'}
        return (lati,long), nns

    def filter_area(self, ll, minx, maxx, miny, maxy, zoom):
        x, y, _ = self.lat_lon_to_x_y(ll[0], ll[1], zoom)
        if x > minx and x < maxx and y > miny and y < maxy:
            return True
        return False

    def convertMasksToSegmentation(self, file = 'train', segmentation_array = None, clean_function=None, mask_file = 'mask', label_file = 'labels'):
        '''Used to label pixels with an integer value corresponding to the order of the segmentation array'''
        self.segmentation_array = segmentation_array
        self.check_and_create_folder(f'{self.parent_directory}/{label_file}/{file}')
        file_names = [o.name for o in os.scandir(f'{self.parent_directory}/{mask_file}/{file}')]
        existing_files = [f'{o.name}' for o in os.scandir(f'{self.parent_directory}/{label_file}/{file}')]
        for fn in file_names:
            if fn not in existing_files:
                orig = im.open(f'{self.parent_directory}/{mask_file}/{file}/{fn}')
                width, height = orig.size
                if clean_function:
                    clean_function(orig)
                m = np.array([self.pxToSeg(d) for d in orig.getdata()])
                m = m.reshape((-1,width))
                m = m.astype(float)
                img = im.fromarray(m)
                img = img.convert('RGB')
                img.save(f'{self.parent_directory}/{label_file}/{file}/{fn}')

    def pxToSeg(self, pixel):
        return np.where([pixel == i for i in self.segmentation_array])[0][0]

    def number_of_tiles(self, top_left_lon:float, top_left_lat:float, bottom_right_lon:float, bottom_right_lat:float, zoom:int):
        '''Get the number of tiles in an area defined by upper left and lower right coordinates for a given zoom'''
        tl_x, tl_y, _ = self.lat_lon_to_x_y(top_left_lat, top_left_lon, zoom)
        br_x, br_y, _ = self.lat_lon_to_x_y(bottom_right_lat, bottom_right_lon, zoom)
        tot = int((abs(br_x - tl_x) + 1) * (abs(tl_y - br_y) + 1))
        return tot

    def convertToRadians(self, degrees):
        '''Simply convert Degrees to Radians'''
        return degrees * math.pi / 180

    def lat_lon_to_x_y(self, lat_deg, lon_deg, zoom):
        '''Convert Latitude/Longitude coordinates to x/y coordinates'''
        n = 2**zoom
        lat_rad = self.convertToRadians(lat_deg)
        xtile = n * ((lon_deg + 180) / 360)
        ytile = n * (1 - (math.log( math.tan(lat_rad) + (1 / math.cos(lat_rad)) ) / math.pi)) / 2
        return xtile, ytile, zoom

    def x_y_lat_lon(self, x, y, zoom):
        '''Convert x/y coordinates to Latitude/Longitude coordinates'''
        n = 2**zoom
        lon_deg = x / n * 360.0 - 180.0
        lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * y / n)))
        lat_deg = lat_rad * 180.0 / math.pi
        return lat_deg, lon_deg

    def get_lats_lons_search(self, search_string:str = 'Den Haag, museum, gallery', minmax_lonlat:list = [4.244794, 4.349174, 52.068414,52.087417], limit:int = 20):
        res = self.service_geocoder.forward(f'\"{search_string}\"', bbox = minmax_lonlat, limit = limit)
        gj = res.geojson()
        name = []
        lat = []
        lon = []
        weights = []
        for l in gj['features']:
            name.append(l['text'])
            lat.append(l['geometry']['coordinates'][1])
            lon.append(l['geometry']['coordinates'][0])
            weights.append(1)
        return pd.DataFrame({'name' : name, 'lat' : lat, 'lon' : lon, 'weight' : weights})

    def search_lats_lons(self, search_string:str = 'Den Haag, museum, gallery', minmax_lonlat:list = [4.244794, 4.349174, 52.068414,52.087417], limit:int = 20):
        out = self.get_lats_lons_search(search_string, minmax_lonlat, limit)[['lat','lon','weight']]
        lat_max = out['lat'].max()
        lat_min = out['lat'].min()
        lon_max = out['lon'].max()
        lon_min = out['lon'].min()
        return [tuple(r) for r in out.values.tolist()], lat_max, lat_min, lon_max, lon_min

    def create_rectangle_polygon(self, center:tuple, size_func, colour:str = "#BE00FF", fill_opacity:float = 1):
        '''Creates a json describing a rectangle that is sent to Mapbox to be drawn on the request image.'''
        size = size_func(center[2])
        tl = [center[1] - size, center[0] + size]
        tr = [center[1] + size, center[0] + size]
        br = [center[1] + size, center[0] - size]
        bl = [center[1] - size, center[0] - size]
        return {'type' : 'Feature', 'geometry' : {'type' : 'Polygon', 'coordinates' : [[tl,tr,br,bl,tl]]}, 'properties' : {'stroke' : colour, 'fill' : colour, 'fill-opacity' : fill_opacity}}

# Cell
def create_rectange_polygon(center:tuple, size_func, colour:str = "#BE00FF", fill_opacity:float = 1):
    '''Creates a json describing a rectangle that is sent to Mapbox to be drawn on the request image.'''
    size = size_func(center[2])
    tl = [center[1] - size, center[0] + size]
    tr = [center[1] + size, center[0] + size]
    br = [center[1] + size, center[0] - size]
    bl = [center[1] - size, center[0] - size]
    return {'type' : 'Feature', 'geometry' : {'type' : 'Polygon', 'coordinates' : [[tl,tr,br,bl,tl]]}, 'properties' : {'stroke' : colour, 'fill' : colour, 'fill-opacity' : fill_opacity}}

# Cell
def get_quad_grid(lat, lon, lat_dif, lon_dif, num_on_axis = 2):
    tuple_list = []
    for la in range(num_on_axis):
        for lo in range(num_on_axis):
            tuple_list.append((lat - la*lat_dif, lon + lo*lon_dif, lat - (la + 1)*lat_dif, lon + (lo + 1)*lon_dif))
    return tuple_list

# Cell
def generate_train_valid_test(data, valid_per = 0.1, test_per = 0.1):
    '''Function to split list into train, valid and test sets'''
    train_ll = []
    valid_ll = []

    test_len = int(test_per*len(data))
    test_idx = np.random.choice(2*test_len,test_len,replace = False)
    test_ll = [ll for i, ll in enumerate(data[:2*test_len]) if i in test_idx]

    rest_data = [d for i, d in enumerate(data) if i not in test_idx]

    valid_len = int(valid_per*len(data))
    valid_idx = np.random.choice(len(rest_data),valid_len,replace = False)

    for i, d in enumerate(rest_data):
        if i in valid_idx:
            valid_ll.append(d)
        else:
            train_ll.append(d)

    assert(len(train_ll) + len(valid_ll) +  len(test_ll) == len(data))

    return {'train':train_ll, 'valid':valid_ll, 'test':test_ll}