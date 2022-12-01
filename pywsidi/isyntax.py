import os
import traceback

from lxml import etree as ET
import base64
import io
from PIL import Image, ImageDraw

def getPadBytesString(pad_char, input_text):

    input_str = base64.b64decode(input_text).decode('utf-8')

    input_byte = input_text.encode('utf-8')

    output_string = ''
    for n in range(len(input_str)):
         output_string += pad_char

    replace_byte = base64.b64encode(output_string.encode('utf-8'))
    return replace_byte, input_byte

def getPadBytesImage(input_text, x_size, y_size):

    last_char = input_text[-1]

    input_text = input_text.replace('\n','')

    new_image = generate_image(x_size, y_size)

    while(len(new_image) > len(input_text)):
        x_size = x_size - 10
        y_size = y_size - 10
        new_image = generate_image(x_size, y_size)

    for n in range((len(input_text) - len(new_image))):
        new_image += '='

    output_string = base64Split(new_image)
    # if if input_text ends with \n replace it
    if last_char == '\n':
        output_string = output_string + '\n'

    replace_byte = output_string.encode('utf-8')

    return replace_byte

def generate_image(x, y, image_text1=None, image_text2=None):
    img = Image.new('RGB', (x, y), color=(73, 109, 137))

    d = ImageDraw.Draw(img)
    d.text((100, 100), "REMOVED DATA 1", fill=(255, 255, 0))
    d.text((100, 130), "REMOVED DATA 2", fill=(255, 255, 0))

    with io.BytesIO() as output:
        img.save(output, format='JPEG')
        contents = output.getvalue()
        base64_bytes = base64.b64encode(contents)
        base64_string = base64_bytes.decode("utf-8")

    return base64_string

def base64Split(a_string):

    split_strings = []
    n = 60
    for index in range(0, len(a_string), n):
        split_strings.append(a_string[index: index + n])

    payload = ''
    for str in split_strings:
        payload += str + '\n'

    return payload[:-1]

def parseXMLheader(header_data, image_text1=None, image_text2=None):

    # create element tree object
    root = ET.fromstring(header_data)

    for data_object in root.iter('DataObject'):

        if data_object.attrib['ObjectType'] == 'DPUfsImport':
            for child in data_object:
                if (child.attrib['Name'] == 'PIM_DP_UFS_BARCODE'):

                    # start new method
                    replace_byte, input_byte = getPadBytesString('-', child.text)
                    header_data = header_data.replace(input_byte, replace_byte)
                    # end new method

                if (child.attrib['Name'] == 'DICOM_DEVICE_SERIAL_NUMBER'):

                    original_sn = child.text
                    new_sn = ''
                    for n in range(len(original_sn)):
                        new_sn += '_'

                    # start new method
                    header_data = header_data.replace(original_sn.encode('utf-8'), new_sn.encode('utf-8'))
                    # end new method

        if data_object.attrib['ObjectType'] == 'DPScannedImage':
            #print('data_object attrib ' + str(data_object.attrib))
            isLabel = False
            isMacro = False

            for child in data_object:
                if (child.attrib['Name'] == 'PIM_DP_IMAGE_TYPE'):
                    if child.text == 'WSI':
                        isLabel = False
                        isMacro = False
                    if child.text == 'LABELIMAGE':
                        isLabel = True
                        isMacro = False
                    if child.text == 'MACROIMAGE':
                        isLabel = False
                        isMacro = True

                if(isLabel and (child.attrib['Name'] == 'PIM_DP_IMAGE_DATA')):

                    # start new method
                    replace_byte = getPadBytesImage(child.text, 796, 826)
                    header_data = header_data.replace(child.text.encode('utf-8'), replace_byte)
                    # end new method


                #if(isMacro and (child.attrib['Name'] == 'PIM_DP_IMAGE_DATA')):

                    # start new method
                    replace_byte = getPadBytesImage(child.text, 1688, 826)
                    header_data = header_data.replace(child.text.encode('utf-8'), replace_byte)
                    # end new method

    #return new_header
    return header_data

def getisyntaxheader(file_path):

    with open(file_path, 'rb') as f:
        s = f.read()
    header_location = s.find(b'\x0D\x0A\x04')

    with open(file_path, 'rb') as f:
        header_data = f.read(header_location)

    return header_location, header_data

def deident_isyntax_file(original_file_path, deident_file_path):
    try:
        '''
        iSyntax files contain a XML header, with base64 encoded preview and label images.
        The WSI files are stored after the XML in a binary format
        '''

        '''
        Todo:
        -Currently, identifiable information such as preview and label images are overwritten with a 
        new image.  Any overwritten information is padded (Base64) to the original size.  
        The location of the header size should be identified and adjusted to prevent padding.  
        '''

        #Determine the header location an extract the header XML
        header_location, header_xml = getisyntaxheader(original_file_path)

        #Determine the image data location
        data_location = os.path.getsize(original_file_path) - header_location

        '''
        Remove identifiable information from slide header, this list is not guaranteed to be exhaustive
        
        This process includes:
        Removing: PIM_DP_UFS_BARCODE # Possible CASE information
        Removing: DICOM_DEVICE_SERIAL_NUMBER # Scanner SN
        Replacing: LABELIMAGE #Possible case ids and names on slide label
        Replacing: MACROIMAGE #Possible case ids and names on slide label
        '''
        header = parseXMLheader(header_xml)

        #Create a new file with a deidentified header and original tile data
        with open(deident_file_path, "wb") as newfile, open(original_file_path, "rb") as original:
            newfile.write(header)
            newfile.write(original.read()[-data_location:])
        return True
    except:
        traceback.print_exc()
        return False

