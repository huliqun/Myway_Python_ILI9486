# Copyright (c) 2016 myway work
# Author: Liqun Hu
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
import numbers
import time
import numpy as np

import Image
import ImageDraw

import Adafruit_GPIO as GPIO
import Adafruit_GPIO.SPI as SPI


# Constants for interacting with display registers.
ILI9486_TFTWIDTH    = 320
ILI9486_TFTHEIGHT   = 480

ILI9486_NOP         = 0x00
ILI9486_SWRESET     = 0x01
ILI9486_RDDID       = 0x04
ILI9486_RDDST       = 0x09

ILI9486_SLPIN       = 0x10
ILI9486_SLPOUT      = 0x11
ILI9486_PTLON       = 0x12
ILI9486_NORON       = 0x13

ILI9486_RDMODE      = 0x0A
ILI9486_RDMADCTL    = 0x0B
ILI9486_RDPIXFMT    = 0x0C
ILI9486_RDIMGFMT    = 0x0A
ILI9486_RDSELFDIAG  = 0x0F

ILI9486_INVOFF      = 0x20
ILI9486_INVON       = 0x21
ILI9486_GAMMASET    = 0x26
ILI9486_DISPOFF     = 0x28
ILI9486_DISPON      = 0x29

ILI9486_CASET       = 0x2A
ILI9486_PASET       = 0x2B
ILI9486_RAMWR       = 0x2C
ILI9486_RAMRD       = 0x2E

ILI9486_PTLAR       = 0x30
ILI9486_MADCTL      = 0x36
ILI9486_PIXFMT      = 0x3A

ILI9486_FRMCTR1     = 0xB1
ILI9486_FRMCTR2     = 0xB2
ILI9486_FRMCTR3     = 0xB3
ILI9486_INVCTR      = 0xB4
ILI9486_DFUNCTR     = 0xB6

ILI9486_PWCTR1      = 0xC0
ILI9486_PWCTR2      = 0xC1
ILI9486_PWCTR3      = 0xC2
ILI9486_PWCTR4      = 0xC3
ILI9486_PWCTR5      = 0xC4
ILI9486_VMCTR1      = 0xC5
ILI9486_VMCTR2      = 0xC7

ILI9486_RDID1       = 0xDA
ILI9486_RDID2       = 0xDB
ILI9486_RDID3       = 0xDC
ILI9486_RDID4       = 0xDD

ILI9486_GMCTRP1     = 0xE0
ILI9486_GMCTRN1     = 0xE1

ILI9486_PWCTR6      = 0xFC

ILI9486_BLACK       = 0x0000
ILI9486_BLUE        = 0x001F
ILI9486_RED         = 0xF800
ILI9486_GREEN       = 0x07E0
ILI9486_CYAN        = 0x07FF
ILI9486_MAGENTA     = 0xF81F
ILI9486_YELLOW      = 0xFFE0  
ILI9486_WHITE       = 0xFFFF


def color565(r, g, b):
    """Convert red, green, blue components to a 16-bit 565 RGB value. Components
    should be values 0 to 255.
    """
    return ((r & 0xF0) << 8) | ((g & 0xFC) << 3) | (b >> 3)

def image_to_data(image):
    """Generator function to convert a PIL image to 16-bit 565 RGB bytes."""
    #NumPy is much faster at doing this. NumPy code provided by:
    #Keith (https://www.blogger.com/profile/02555547344016007163)
    pb = np.array(image.convert('RGB')).astype('uint16')
#    color = ((pb[:,:,0] & 0xF8) << 8) | ((pb[:,:,1] & 0xFC) << 3) | (pb[:,:,2] >> 3)
#    return np.dstack(((color >> 8) & 0xFF, color & 0xFF)).flatten().tolist()
    return np.dstack((pb[:,:,0] & 0xFC, pb[:,:,1] & 0xFC, pb[:,:,2] & 0xFC)).flatten().tolist()
#    pixels = image.convert('RGB').load()  
#    width, height = image.size  
#    for y in range(height):  
#        for x in range(width):  
#            r,g,b = pixels[(x,y)]  
##            color = color565(r, g, b)  
#            #yield (color >> 8) & 0xFF  
#            #yield color & 0xFF  
#            yield r 
#            yield g  
#            yield b 


class ILI9486(object):
    """Representation of an ILI9486 TFT LCD."""

    def __init__(self, dc, spi, rst=None, gpio=None, width=ILI9486_TFTWIDTH,
        height=ILI9486_TFTHEIGHT):
        """Create an instance of the display using SPI communication.  Must
        provide the GPIO pin number for the D/C pin and the SPI driver.  Can
        optionally provide the GPIO pin number for the reset pin as the rst
        parameter.
        """
        self._dc = dc
        self._rst = rst
        self._spi = spi
        self._gpio = gpio
        self.width = width
        self.height = height
        if self._gpio is None:
            self._gpio = GPIO.get_platform_gpio()
        # Set DC as output.
        self._gpio.setup(dc, GPIO.OUT)
        # Setup reset as output (if provided).
        if rst is not None:
            self._gpio.setup(rst, GPIO.OUT)
        # Set SPI to mode 0, MSB first.
        spi.set_mode(2)
        spi.set_bit_order(SPI.MSBFIRST)
        spi.set_clock_hz(64000000)
        # Create an image buffer.
        self.buffer = Image.new('RGB', (width, height))

    def send(self, data, is_data=True, chunk_size=4096):
        """Write a byte or array of bytes to the display. Is_data parameter
        controls if byte should be interpreted as display data (True) or command
        data (False).  Chunk_size is an optional size of bytes to write in a
        single SPI transaction, with a default of 4096.
        """
        # Set DC low for command, high for data.
        self._gpio.output(self._dc, is_data)
        # Convert scalar argument to list so either can be passed as parameter.
        if isinstance(data, numbers.Number):
            data = [data & 0xFF]
        # Write data a chunk at a time.
        for start in range(0, len(data), chunk_size):
            end = min(start+chunk_size, len(data))
            self._spi.write(data[start:end])

    def command(self, data):
        """Write a byte or array of bytes to the display as command data."""
        self.send(data, False)

    def data(self, data):
        """Write a byte or array of bytes to the display as display data."""
        self.send(data, True)

    def reset(self):
        """Reset the display, if reset pin is connected."""
        if self._rst is not None:
            self._gpio.set_high(self._rst)
            time.sleep(0.005)
            self._gpio.set_low(self._rst)
            time.sleep(0.02)
            self._gpio.set_high(self._rst)
            time.sleep(0.150)

    def _init(self):
        # Initialize the display.  Broken out as a separate function so it can
        # be overridden by other displays in the future.
        self.command(0xB0)
        self.data(0x00)
        self.command(0x11)
        time.sleep(0.020)
    
        self.command(0x3A)
        self.data(0x66)

        self.command(0x0C)
        self.data(0x66)

        #self.command(0xB6)
        #self.data(0x00)
        #self.data(0x42)
        #self.data(0x3B)

        self.command(0xC2)
        self.data(0x44)

        self.command(0xC5)
        self.data(0x00)
        self.data(0x00)
        self.data(0x00)
        self.data(0x00)
        
        self.command(0xE0)
        self.data(0x0F)
        self.data(0x1F)
        self.data(0x1C)
        self.data(0x0C)
        self.data(0x0F)
        self.data(0x08)
        self.data(0x48)
        self.data(0x98)
        self.data(0x37)
        self.data(0x0A)
        self.data(0x13)
        self.data(0x04)
        self.data(0x11)
        self.data(0x0D)
        self.data(0x00)

        self.command(0xE1)
        self.data(0x0F)
        self.data(0x32)
        self.data(0x2E)
        self.data(0x0B)
        self.data(0x0D)
        self.data(0x05)
        self.data(0x47)
        self.data(0x75)
        self.data(0x37)
        self.data(0x06)
        self.data(0x10)
        self.data(0x03)
        self.data(0x24)
        self.data(0x20)
        self.data(0x00)
    
        self.command(0xE2)
        self.data(0x0F)
        self.data(0x32)
        self.data(0x2E)
        self.data(0x0B)
        self.data(0x0D)
        self.data(0x05)
        self.data(0x47)
        self.data(0x75)
        self.data(0x37)
        self.data(0x06)
        self.data(0x10)
        self.data(0x03)
        self.data(0x24)
        self.data(0x20)
        self.data(0x00)
            
        self.command(0x36)
        self.data(0x88) #change the direct

        self.command(0x11)
        self.command(0x29)

    def begin(self):
        """Initialize the display.  Should be called once before other calls that
        interact with the display are called.
        """
        self.reset()
        self._init()    
    
    def set_window(self, x0=0, y0=0, x1=None, y1=None):
        """Set the pixel address window for proceeding drawing commands. x0 and
        x1 should define the minimum and maximum x pixel bounds.  y0 and y1 
        should define the minimum and maximum y pixel bound.  If no parameters 
        are specified the default will be to update the entire display from 0,0
        to 239,319.
        """
        if x1 is None:
            x1 = self.width-1
        if y1 is None:
            y1 = self.height-1
        self.command(0x2A)        # Column addr set
        self.data(x0 >> 8)
        self.data(x0 & 0xFF)                    # XSTART 
        self.data(x1 >> 8)
        self.data(x1 & 0xFF)                    # XEND
        self.command(0x2B)        # Row addr set
        self.data(y0 >> 8)
        self.data(y0 & 0xFF)                    # YSTART
        self.data(y1 >> 8)
        self.data(y1 & 0xFF)                    # YEND
        self.command(0x2C)        # write to RAM

    def display(self, image=None):
        """Write the display buffer or provided image to the hardware.  If no
        image parameter is provided the display buffer will be written to the
        hardware.  If an image is provided, it should be RGB format and the
        same dimensions as the display hardware.
        """
        # By default write the internal buffer to the display.
        if image is None:
            image = self.buffer
        # Set address bounds to entire display.
        self.set_window()
        # Convert image to array of 16bit 565 RGB data bytes.
        # Unfortunate that this copy has to occur, but the SPI byte writing
        # function needs to take an array of bytes and PIL doesn't natively
        # store images in 16-bit 565 RGB format.
        pixelbytes = list(image_to_data(image))
        # Write data to hardware.
        self.data(pixelbytes)

    def clear(self, color=(0,0,0)):
        """Clear the image buffer to the specified RGB color (default black)."""
        width, height = self.buffer.size
        self.buffer.putdata([color]*(width*height))

    def draw(self):
        """Return a PIL ImageDraw instance for 2D drawing on the image buffer."""
        return ImageDraw.Draw(self.buffer)
