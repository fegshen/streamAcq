"""
Interfaces of routines for acquisition.
"""

from abc import abstractmethod, ABCMeta
import asyncio

class Acquisition(metaclass=ABCMeta):

    @abstractmethod
    def bind_to_queue(self, data_queue : asyncio.Queue):
        """
        bind the acquisition to a data_queue such that acquisition will send data into the data_queue.
        The data must be a instance from AcquireData.
        """
        pass

    @abstractmethod
    async def start(self):
        """
        To start the acquisition in a asynchronous way.
        """
        pass

    @abstractmethod
    def stop(self):
        """
        To stop the acquisition.
        """
        pass

    @abstractmethod
    def is_closing(self):
        """
        To check if the acquisition is running.
        """
        pass