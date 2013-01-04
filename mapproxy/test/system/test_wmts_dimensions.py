# This file is part of the MapProxy project.
# Copyright (C) 2011 Omniscale <http://omniscale.de>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import with_statement, division

import functools

from cStringIO import StringIO
from mapproxy.request.wmts import (
    WMTS100TileRequest, WMTS100CapabilitiesRequest
)
from mapproxy.test.image import is_jpeg, create_tmp_image
from mapproxy.test.http import MockServ
from mapproxy.test.helper import validate_with_xsd
from mapproxy.test.system import module_setup, module_teardown, SystemTest, make_base_config
from nose.tools import eq_

test_config = {}
base_config = make_base_config(test_config)

def setup_module():
    module_setup(test_config, 'wmts_dimensions.yaml', with_cache_data=True)

def teardown_module():
    module_teardown(test_config)

ns_wmts = {
    'wmts': 'http://www.opengis.net/wmts/1.0',
    'ows': 'http://www.opengis.net/ows/1.1',
    'xlink': 'http://www.w3.org/1999/xlink'
}

def eq_xpath(xml, xpath, expected, namespaces=None):
    eq_(xml.xpath(xpath, namespaces=namespaces)[0], expected)

eq_xpath_wmts = functools.partial(eq_xpath, namespaces=ns_wmts)

DIMENSION_LAYER_BASE_REQ = (
    '/service1?styles=&format=image%2Fpng&height=256'
    '&bbox=-20037508.3428,0.0,0.0,20037508.3428'
    '&layers=foo,bar&service=WMS&srs=EPSG%3A900913'
    '&request=GetMap&width=256&version=1.1.1'
)
NO_DIMENSION_LAYER_BASE_REQ = DIMENSION_LAYER_BASE_REQ.replace('/service1?', '/service2?')

TEST_TILE = create_tmp_image((256, 256))

class TestWMTS(SystemTest):
    config = test_config
    def setup(self):
        SystemTest.setup(self)

    def test_capabilities(self):
        resp = self.app.get('/wmts/myrest/1.0.0/WMTSCapabilities.xml')
        xml = resp.lxml
        assert validate_with_xsd(xml, xsd_name='wmts/1.0/wmtsGetCapabilities_response.xsd')
    #     eq_(len(xml.xpath('//wmts:Layer', namespaces=ns_wmts)), 4)
    #     eq_(len(xml.xpath('//wmts:Contents/wmts:TileMatrixSet', namespaces=ns_wmts)), 4)


    def test_get_tile_valid_dimension(self):
        serv = MockServ(42423)
        serv.expects(DIMENSION_LAYER_BASE_REQ + '&Time=2012-11-15T00:00:00&elevation=1000').returns(TEST_TILE)
        with serv:
            resp = self.app.get('/wmts/dimension_layer/GLOBAL_MERCATOR/2012-11-15T00:00:00/1000/01/0/0.png')
        eq_(resp.content_type, 'image/png')

    def test_get_tile_invalid_dimension(self):
        self.check_invalid_parameter('/wmts/dimension_layer/GLOBAL_MERCATOR/2042-11-15T00:00:00/default/01/0/0.png')

    def test_get_tile_default_dimension(self):
        serv = MockServ(42423)
        serv.expects(DIMENSION_LAYER_BASE_REQ + '&Time=2012-11-15T00:00:00&elevation=0').returns(TEST_TILE)
        with serv:
            resp = self.app.get('/wmts/dimension_layer/GLOBAL_MERCATOR/default/default/01/0/0.png')
        eq_(resp.content_type, 'image/png')

    def test_get_tile_invalid_no_dimension_source(self):
        self.check_invalid_parameter('/wmts/no_dimension_layer/GLOBAL_MERCATOR/2042-11-15T00:00:00/default/01/0/0.png')

    def test_get_tile_default_no_dimension_source(self):
        serv = MockServ(42423)
        serv.expects(NO_DIMENSION_LAYER_BASE_REQ).returns(TEST_TILE)
        with serv:
            resp = self.app.get('/wmts/no_dimension_layer/GLOBAL_MERCATOR/default/default/01/0/0.png')
        eq_(resp.content_type, 'image/png')

    def test_get_tile_kvp_valid_dimension(self):
        serv = MockServ(42423)
        serv.expects(DIMENSION_LAYER_BASE_REQ + '&Time=2012-11-15T00:00:00&elevation=1000').returns(TEST_TILE)
        with serv:
            resp = self.app.get('/service?service=wmts&request=GetTile&version=1.0.0&tilematrixset=GLOBAL_MERCATOR&tilematrix=01&tilecol=0&tilerow=0&format=png&layer=dimension_layer&style=')
        eq_(resp.content_type, 'image/png')


    def check_invalid_parameter(self, url):
        resp = self.app.get(url, status=400)
        xml = resp.lxml
        eq_(resp.content_type, 'text/xml')
        assert validate_with_xsd(xml, xsd_name='ows/1.1.0/owsExceptionReport.xsd')
        eq_xpath_wmts(xml, '/ows:ExceptionReport/ows:Exception/@exceptionCode',
            'InvalidParameterValue')

