# -*- coding: utf-8 -*-

"""
    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

    Development Team: Stanislav WEB
"""

import importlib
import random
from src.core import helper
from urllib3 import ProxyManager
from urllib3.exceptions import DependencyWarning, MaxRetryError, ProxySchemeUnknown, ReadTimeoutError

from .exceptions import ProxyRequestError
from .providers import RequestProvider, HeaderProvider


class Proxy(RequestProvider, HeaderProvider):
    """Proxy class"""


    def __init__(self, config, debug=0, **kwargs):
        """
        Proxy instance
        :param src.lib.browser.config.Config config:
        :param int debug: debug flag
        :raise ProxyRequestError
        """

        try:
            self.__tpl = kwargs.get('tpl')
            self.__proxylist = kwargs.get('proxy_list')

            HeaderProvider.__init__(self, config, agent_list=kwargs.get('agent_list'))

            if type(self.__proxylist) is not list or 0 == len(self.__proxylist):
                raise TypeError('Proxy list empty or has invalid format')

        except (TypeError, ValueError) as e:
            raise ProxyRequestError(e.message)

        self.__cfg = config
        self.__debug = False if debug < 2 else True

        if True is self.__debug:
            self.__tpl.debug(key='proxy_pool_start')

    def __proxy_pool(self):
        """
        Create Proxy connection pool
        :raise ProxyRequestError
        :return: urllib3.HTTPConnectionPool
        """

        try:

            self.__server = self.__get_random_proxyserver()

            if self.__get_proxy_type(self.__server) == 'socks':

                if not self.__pm:

                    module = importlib.import_module('urllib3.contrib.socks')
                    self.__pm = getattr(module, 'SOCKSProxyManager')

                pool = self.__pm(self.__server, num_pools=self.__cfg.threads, timeout=self.__cfg.timeout, block=True)
            else:
                pool = ProxyManager(self.__server, num_pools=self.__cfg.threads, timeout=self.__cfg.timeout, block=True)
            return pool
        except (DependencyWarning, ProxySchemeUnknown, ImportError) as e:
            raise ProxyRequestError(e)

    def request(self, url):
        """
        Client request using Proxy
        :param str url: request uri
        :return: urllib3.HTTPResponse
        """

        pool = self.__proxy_pool()

        try:
            response = pool.request(self.__cfg.method, url,
                                    headers=self._headers,
                                    retries=self.__cfg.retries,
                                    redirect=False)
            return response
        except MaxRetryError:
            self.__tpl.warning(key='proxy_max_retry_error', url=helper.parse_url(url).path, proxy=self.__server)
            pass
        except ReadTimeoutError:
            self.__tpl.warning(key='read_timeout_error', url=helper.parse_url(url).path)
            pass

    def __get_random_proxyserver(self):
        """
        Get random server from proxy list
        :return: str
        """

        index = random.randrange(0, len(self.__proxylist))
        server = self.__proxylist[index].strip()

        return server

    def __get_proxy_type(self, server):
        """
        Set proxy type
        :param str server:
        :return: str
        """

        if 'socks' in server:
            return 'socks'
        elif 'https' in server:
            return 'https'
        else:
            return 'http'
