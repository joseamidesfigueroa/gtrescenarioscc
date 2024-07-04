#!/bin/bash

cdo -f nc mergetime *.nc ISIMIP.nc
cdo sellonlatbox,-94,-67,6,21 ISIMIP.nc ISIMIP_recortado.nc
