import settings
import glob
import h5py
import icepyx as ipx
import json
import math
import multiprocessing
import os
import re
import sys
import time
import tqdm


STANDARD_DIMENSIONS_VALUES = [
    ## (Standard Dimension, Path End)
    ("X", "longitude"),
    ("Y", "latitude"),
    ("Z", "h_li"),
    ("GpsTime", "delta_time"),
]

CUSTOM_DIMENSIONS_VALUES = [
    ## (Custom Dimension, Path End, Value Type)
    ("atl06_quality_summary", "atl06_quality_summary", "int8"),
    ("h_li_sigma", "h_li_sigma", "float32"),
    ("segment_id", "segment_id", "int32"),
    ("sigma_geo_h", "sigma_geo_h", "float32")
]

CUSTOM_FILE_DIMENSIONS = [
    # (Dimension Name, Path, Value Type)
    ('CycleNumber', 'orbit_info/cycle_number', "int8"),
]

CUSTOM_AUX_DIMENSIONS = [
    # (Dimension Name, N/A, Value Type)
    # This is for dimensions that are added that are not represented
    # in the file itself.
    ('GranuleId', None, "int32"),
]

FILTER_STAGE =  {
    "type":"filters.range",
    "limits":"Z[0:100000]",
}

REPROJECTION_STAGE = {
    "type":"filters.reprojection",
    "in_srs":"EPSG:4326",
    "out_srs":"EPSG:32757",
}

BEAMS = ['gt1l', 'gt1r', 'gt2l', 'gt2r', 'gt3l', 'gt3r']

def full_run(path):
    start_time = time.time()
    get_files(path)
    sort_files(path)
    process_cycles(path)
    print ('Full Run Time:', time.time() - start_time)

def get_files(path):

    SHORT_NAME = 'ATL06'
    region = ipx.core.query.Query(SHORT_NAME, settings.SPATIAL_EXTENT, settings.DATE_RANGE)
    region.earthdata_login(settings.EARTHDATA_UID, settings.EARTHDATA_EMAIL)
    region.order_granules(email=False)
    region.download_granules(path)

def sort_files(base_dir):
    files = glob.glob(base_dir + '/*h5')
    for file_path in tqdm.tqdm(files):
        file_name = os.path.basename(file_path)
        f = h5py.File(file_path, 'r')
        cycle_number = f['orbit_info/cycle_number'][0]
        output_dir  = os.path.join(base_dir, str(cycle_number))
        if not os.path.isdir(output_dir):
            os.mkdir(output_dir)
        os.rename(file_path, os.path.join(output_dir, file_name))

def process_cycles(base_dir):
    for cycle_dir in glob.glob(os.path.join(base_dir, '*/')):
        print ("Working on: " + cycle_dir)
        output_dir = process_raw_files_to_laz(cycle_dir)
        entwine_build(output_dir)

def process_raw_files_to_laz(base_dir):
    start_time = time.time()
    ## Create Output Folder if it doesn't already exists
    output_dir  = os.path.join(base_dir, 'output')
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)
    #pool = multiprocessing.Pool()
    files = glob.glob(base_dir + '/*h5')
    for file_path in tqdm.tqdm(files):
        #pool.apply_async(convert_file, (base_dir, output_dir, file_path))
        convert_file(file_path, base_dir, output_dir)
    print ('LAZ Conversion Time: ', time.time() - start_time)
    return output_dir

def convert_file(file_path, base_dir, output_dir):
    base_command = "sudo docker run --rm -it -v '{base_dir}:{base_dir}' pdal/pdal pdal pipeline ".format(**{'base_dir': base_dir})
    file, extension = os.path.splitext(file_path)
    input_file = file_path
    base_filename =  file.split('/')[-1]
    output_file = '%s/%s.laz' % (output_dir, base_filename)
    pipeline  = build_laz_conversion_pipeline(input_file, output_file)
    pipeline_path = os.path.join(output_dir, base_filename + '.json' )
    with open(pipeline_path, 'w') as pipeline_file:
        json.dump(pipeline, pipeline_file)
    command = base_command + pipeline_path
    os.system(command)
    os.remove(pipeline_path)

def build_laz_conversion_pipeline(input_file, output_file):
    pipeline = []
    file_id = get_granule_id(input_file)
    f = h5py.File(input_file, 'r')
    beam_id = 0
    beam_name_stages = []
    for beam in BEAMS:
        base_path = "%s/land_ice_segments/" % beam
        stage = {
            "type": "readers.hdf",
            "filename": input_file,
            "dimensions": {},
            "tag": beam
        }
        for key, value in STANDARD_DIMENSIONS_VALUES:
            stage["dimensions"][key] = base_path + value
        for key, value, value_type in CUSTOM_DIMENSIONS_VALUES:
            stage["dimensions"][key] = base_path +  value
        pipeline.append(stage)
        dim_stage = {
            "type": "filters.ferry",
            "inputs": [beam],
            "dimensions": "=>GranuleId,=>ReturnNumber,=>CycleNumber",
            "tag": beam + "_dim"
        }
        pipeline.append(dim_stage)
        beam_name_stage = {
            "type": "filters.assign",
            "inputs": [beam + "_dim"],
            "assignment": "ReturnNumber[:]=%s" % beam_id,
            "tag": beam + "_id_stage"
        }
        pipeline.append(beam_name_stage)
        beam_id += 1
    GRANULE_ID_STAGE = {
        "type": "filters.assign",
        "inputs": [beam + "_id_stage" for beam in BEAMS],
        "assignment": "GranuleId[:]=%s" % file_id,
    }
    pipeline.append(GRANULE_ID_STAGE)
    for key, value, vt in CUSTOM_FILE_DIMENSIONS:
        custom_file_stage = {
            "type": "filters.assign",
            "assignment": "%s[:]=%s" % (key, f[value][0])
        }
        pipeline.append(custom_file_stage)
    pipeline.append(FILTER_STAGE)
    #pipeline.append(REPROJECTION_STAGE)
    extra_dims = (', ').join('%s=%s' % (key, value_type) for key, value, value_type in CUSTOM_DIMENSIONS_VALUES + CUSTOM_FILE_DIMENSIONS + CUSTOM_AUX_DIMENSIONS)
    writer_stage = {
        "type" : "writers.las",
        "filename": output_file,
        "compression":"laszip",
        "minor_version" : "4",
        "extra_dims": extra_dims,
    }
    pipeline.append(writer_stage)
    return pipeline

def entwine_build(base_dir):
    stages = get_stages(settings.STAGES)
    start_time = time.time()
    num_cores = multiprocessing.cpu_count()
    output_path = os.path.join(base_dir, 'entwine')
    check_dir(output_path)
    processed_path = os.path.join(base_dir, 'processed')
    check_dir(processed_path)
    string_dict = {
        'base_dir': base_dir,
        'output_path': output_path,
        'processed_path': processed_path,
        'total_stages': stages,
        'num_cores': num_cores,
    }
    base_command = "sudo docker run --rm -it -v '{base_dir}:{base_dir}' connormanning/entwine build --threads {num_cores} {stages_string} -i {base_dir} -o {output_path}"
    string_dict["stages_string"] = ""
    if stages > 1:
        stages_string = "-s {current_stage} {total_stages}"
        for i in range(1, stages+1):
            string_dict['stages_string'] = stages_string.format(**{'current_stage': i, 'total_stages': stages})
            command = base_command.format(**string_dict)
            os.system(command)
            merge_command = "sudo docker run --rm -it -v '{base_dir}:{base_dir}' connormanning/entwine merge {output_path}"
            command = merge_command.format(**string_dict)
    else:
        command = base_command.format(**string_dict)
        os.system(command)
    # Move all files 
    os.system("mv {base_dir}/*.laz {processed_path}".format(**string_dict))
    print ('Entwine Build Time: ', time.time() - start_time)

def get_stages(num_cores):
    # Get the maximum number of stages to kick off.
    # Number of stages must be a power of 4.
    n = 1
    while math.pow(4, n) <= num_cores:
        n += 1
    return int(math.pow(4, n-1))

def check_dir(path):
    if not os.path.isdir(path):
        os.mkdir(path)

def get_granule_id(input_file):
    try:
        basename = os.path.basename(input_file)
        re_search = re.search("_[0-9]{8}_", basename)
        return int(basename[re_search.start()+1:re_search.end()-1])
    except:
        return 0

def cli():
    path = sys.argv[1]
    print('Storing output: ' + path)
    full_run(path)

if __name__ == "__main__":
    cli()

