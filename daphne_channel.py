from oei import OEI
from logger import logger

class DaphneChannel:
    WAVEFORM_LENGTH = 128

    identifier: str

    data_address: int
    timestamp_address: int
    threshold_address: int

    threshold_adc_units: int

    waveform_data: tuple
    timestamp_data: tuple

    cuentas: int
    contador_ceros: int


    def __init__(self,
                 identifier: str,
                 data_address: int,
                 timestamp_address: int,
                 threshold_address: int,
                 threshold_adc_units: int):
        self.identifier = identifier

        self.data_address = data_address
        self.timestamp_address = timestamp_address
        self.threshold_address = threshold_address
        self.threshold_adc_units = threshold_adc_units

        self.waveform_data = tuple()
        self.timestamp_data = tuple()

        self.cuentas = 0
        self.contador_ceros = 0

    def empty_fifos(self, thing: OEI):
        logger.debug(f"CH {self.identifier} Emptying FIFOS")
        for i in range(256):
            self.read_waveform(thing)
    
    def write_threshold_value(self, thing: OEI, threshold_adc_units = None):

        if threshold_adc_units is None:
            logger.debug(f"CH {self.identifier} Writing threshold value {self.threshold_adc_units}")
            thing.write(self.threshold_address,[self.threshold_adc_units])
            return
        
        logger.debug(f"CH {self.identifier} Writing threshold value {threshold_adc_units}")
        thing.write(self.threshold_address,[threshold_adc_units])

    def read_waveform(self, thing: OEI):
        """ 
        Returns tuple of timestamp and waveform
        (timestamp, waveform)
        """
        waveform = thing.readf(self.data_address, DaphneChannel.WAVEFORM_LENGTH)[2:]
        timestamp = thing.readf(self.timestamp_address, 1)[2:]

        return timestamp, waveform