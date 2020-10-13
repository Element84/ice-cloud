**Project Overview**

Ice Cloud is a [NASA ACCESS](https://earthdata.nasa.gov/esds/competitive-programs/access) project to perform a proof of concept (small scale) transformation of the ICESAT2 ATL06 product into a cloud native, usable, and scalable format for downstream scientific exploitation. This repository includes the code to perform the transformation into the Entwine Point Tile (EPT) format and a series of tutorials on how to use the generated endpoints. EPT is an octree-based storage format that’s encoding-agnostic, lossless, and supports a flexible attribute schema. Additional information about EPT can be found at [entwine.io](https://entwine.io).

**How to Execute EPT Conversion for ATL06 Data**
1. Start by pulling down the repository: 
```
git clone git@repo.element84.com:access/ice-cloud.git
cd ice-cloud
```
2. Make a copy of the [Example Settings](settings.py.example) and save locally as `settings.py`.  Within that file you are able to adjust the spatial and temporal bounds of your query.  You must also populate the `EARTHDATA_UID` and `EARTHDATA_EMAIL` values from your personal EARTHDATA account. If you do not have an accounts, you will need to signup for one at https://urs.earthdata.nasa.gov/users/new
3. Grab the required Docker containers for execution.  See [Get Docker](https://docs.docker.com/get-docker/) for instructions on how to install Docker.
```
docker pull pdal/pdal
docker pull connormanning/entwine
```
4. Install the following pip requirements:
```
h5py==2.10.0
icepyx==0.3.0
tqdm==4.42.1
```
5. Now you are ready to execute the converter!  Simply call the `ept_converter.py` with Python 3.x
`python ept_converter.py`
6. Lastly you will need to enter your EARTHDATA Password when prompted by the script!

**How to Use EPT Data**

In these tutorials we will explore a few simple examples of how to exploit the ATL 06 EPT endpoints.

**Setting Up The Environment - Installing Conda**

If you need to install conda, please follow the [installation instructions](https://conda.io/projects/conda/en/latest/user-guide/install/index.html).

After completing the installation, run the following commands to setup your Conda local [PDAL](https://pdal.io/index.html) environment:

```
    conda create --yes --name pdal-env --channel conda-forge python-pdal
    conda install --name pdal-env --channel conda-forge python-pdal
    conda activate pdal-env
    conda update python-pdal
```

At this point you will now have a local full PDAL conda environment that will allow you to make PDAL CLI commands directly.

**How to work with PDAL and Pipelines**

When working with PDAL you can pass all parameters as a command-line variable, but you are also able to pass the parameters in as a [pipeline](https://pdal.io/pipeline.html).
A pipeline is essentially a  JSON file that contains the following stages:
- [Readers](https://pdal.io/stages/readers.html): instructs PDAL where the file is, what driver to use when reading the file (most file formats will default based on extension), and allows for mapping of custom dimensions.
- [Filters](https://pdal.io/stages/filters.html): instructs PDAL on how to modify/process the points that have been loaded into memory. Examples include reprojection, decimation, colorization, height above ground, etc.
- [Writers](https://pdal.io/stages/writers.html): instructs PDAL on where to write the output and in what format.

To pass a pipeline to PDAL, the command will look like this:
```pdal pipeline <filename.json>```


Now that we have reviewed the basics of how to setup a PDAL environment and are familiar with Pipelines, we are going to dive into a few examples.  The examples will be broken out in the following areas:

**[Filetype Conversions](tutorials/filetype_tutorial.md)**

**[Merging and Filtering](tutorials/merging_filtering_tutorial.md)**

**[Python Operations](tutorials/python_operations_tutorial.md)**