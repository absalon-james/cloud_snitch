import datetime
import time
import logging

from django.core.cache.backends.locmem import LocMemCache
from django.test import TestCase

from api.cache import cache_key
from api import decorators
from api.decorators import cached_result
from api.decorators import cls_cached_result

from mock import patch


logging.getLogger('api.decorators').setLevel(logging.ERROR)


class TestCacheKey(TestCase):

    args = (1, 2, 3)
    kwargs = {'key1': 'val1', 'key2': 'val2', 'key3': 'val3'}

    def test_default(self):
        key = cache_key(self.args, self.kwargs)
        expected = b'LSgxLCAyLCAzKS1bKCdrZXkxJywgJ3ZhbDEnKSwgKCdrZXkyJywgJ3ZhbDInKSwgKCdrZXkzJywgJ3ZhbDMnKV0=' # noqa E501
        self.assertEquals(key, expected)

    def test_prefix(self):
        key = cache_key(self.args, self.kwargs, prefix='test_prefix_123')
        expected = b'dGVzdF9wcmVmaXhfMTIzLSgxLCAyLCAzKS1bKCdrZXkxJywgJ3ZhbDEnKSwgKCdrZXkyJywgJ3ZhbDInKSwgKCdrZXkzJywgJ3ZhbDMnKV0=' # noqa E501
        self.assertEquals(key, expected)

    def test_non_zero_index(self):
        key = cache_key(self.args, self.kwargs, index=1)
        expected = b'LSgyLCAzKS1bKCdrZXkxJywgJ3ZhbDEnKSwgKCdrZXkyJywgJ3ZhbDInKSwgKCdrZXkzJywgJ3ZhbDMnKV0=' # noqa E501
        self.assertEquals(key, expected)


class BaseCacheCase(TestCase):
    def setUp(self):
        self.locmem_cache = LocMemCache('default', {})
        self.locmem_cache.clear()
        self.patch = patch.object(decorators, 'cache', self.locmem_cache)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()


class TestCachedResult(BaseCacheCase):
    def test_default(self):
        @cached_result()
        def test_func():
            return datetime.datetime.utcnow().isoformat()
        v1 = test_func()
        v2 = test_func()
        self.assertEquals(v1, v2)

    def test_with_prefix(self):
        @cached_result(prefix='test_func')
        def test_func():
            return datetime.datetime.utcnow().isoformat()
        v1 = test_func()
        v2 = test_func()
        self.assertEquals(v1, v2)

    def test_timeout(self):
        @cached_result(timeout=1)
        def test_func():
            return datetime.datetime.utcnow().isoformat()
        v1 = test_func()
        time.sleep(2)
        v2 = test_func()
        self.assertNotEquals(v1, v2)


class TestClsCachedResult(BaseCacheCase):
    def test_default(self):
        class SillyTest:
            @cls_cached_result()
            def test_func(self, arg1, arg2):
                return datetime.datetime.utcnow().isoformat()
        obj = SillyTest()
        v1 = obj.test_func('arg1', 'arg2')
        v2 = obj.test_func('arg1', 'arg2')
        self.assertEquals(v1, v2)

    def test_with_prefix(self):
        class SillyTest:
            @cls_cached_result(prefix='test_func')
            def test_func(self, arg1, arg2):
                return datetime.datetime.utcnow().isoformat()
        obj = SillyTest()
        v1 = obj.test_func('arg1', 'arg2')
        v2 = obj.test_func('arg1', 'arg2')
        self.assertEquals(v1, v2)

    def test_timeout(self):
        class SillyTest:
            @cls_cached_result(timeout=1)
            def test_func(self, arg1, arg2):
                return datetime.datetime.utcnow().isoformat()
        obj = SillyTest()
        v1 = obj.test_func('arg1', 'arg2')
        time.sleep(2)
        v2 = obj.test_func('arg1', 'arg2')
        self.assertNotEquals(v1, v2)
