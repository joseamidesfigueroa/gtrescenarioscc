import netCDF4 as nc
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
from scipy.interpolate import RegularGridInterpolator
from scipy.stats import pearsonr, spearmanr

# Cargar datos de la rejilla (CHELSA, ERA5-land, CHIRPS, etc.) usando netCDF4
grid_file = '/home/arw/ISIMIP3a/ISIMIP_recortado.nc'
grid_data = nc.Dataset(grid_file)

# Variables dentro del archivo netCDF (los nombres habrá que adaptarlos en función de la rejilla, en este ejemplo la variable climática es temperatura)
grid_lat = grid_data.variables['lat'][:]
grid_lon = grid_data.variables['lon'][:]
grid_time = grid_data.variables['time'][:]
#grid_targetvar = grid_data.variables['temperature'][:]
grid_targetvar = grid_data.variables['pr'][:]

# Cargar datos de estaciones (archivo de ejemplo 'stations_data.csv')
stations_data = pd.read_csv('/home/arw/ISIMIP3a/stations_data.csv')
stations_data['date'] = pd.to_datetime(stations_data['date'])

# Función para convertir fechas a índices de tiempo en la rejilla 
def convert_time_to_index(time_array, date):
    time_num = nc.date2num(date, units='days since 2000-01-01 00:00:00', calendar='standard')
    time_idx = np.interp(time_num, time_array, np.arange(len(time_array)))
    return time_idx

# Crear el interpolador para los datos de la rejilla (solo local alrededor de la estación para ganar eficiencia computacional)
def create_interpolator(targetvar_data, lat_array, lon_array, lat_station, lon_station):
    lat_idx = np.abs(lat_array - lat_station).argmin()
    lon_idx = np.abs(lon_array - lon_station).argmin()
    # Definir rangos para interpolación local
    lat_range = lat_array[max(0, lat_idx-1):min(len(lat_array), lat_idx+2)]
    lon_range = lon_array[max(0, lon_idx-1):min(len(lon_array), lon_idx+2)]
    targetvar_range = targetvar_data[:, max(0, lat_idx-1):min(len(lat_array), lat_idx+2), max(0, lon_idx-1):min(len(lon_array), lon_idx+2)]
    
    return RegularGridInterpolator(
        (np.arange(len(grid_time)), lat_range, lon_range), 
        targetvar_range,
        bounds_error=False,
        fill_value=None
    )

# Función para extraer valores interpolados de la rejilla para las ubicaciones y fechas de las estaciones
def extract_interpolated_grid_value(lat, lon, date):
    interpolator = create_interpolator(grid_targetvar, grid_lat, grid_lon, lat, lon)
    time_idx = convert_time_to_index(grid_time, date)
    return interpolator((time_idx, lat, lon))

# Aplica la extracción a cada fila del DataFrame de estaciones usando la interpolación local, esto es, agrega una columna 'interpolated_grid_value' al 
# DataFrame stations_data que contiene los valores de la rejilla interpolados para cada estación meteorológica en cada fecha especificada en los datos de la estación. 
# Esto permite posteriormente calcular las diferencias entre los valores observados en las estaciones y los valores interpolados de la rejilla, y realizar
# análisis adicionales, como el cálculo de métricas de error y la generación de gráficos.
stations_data['interpolated_grid_value'] = stations_data.apply(
    lambda row: extract_interpolated_grid_value(row['latitude'], row['longitude'], row['date']),
    axis=1
)
# imprimir el DataFrame con la nueva columna que contiene los datos interpolados localmente en la rejilla
print(stations_data)

# Calcular diferencias y métricas 
stations_data['difference_interpolated'] = stations_data['pr'] - stations_data['interpolated_grid_value']
def calculate_metrics_interpolated(data):
    data = data.dropna()  # Eliminar filas con NaN si es necesario
    if len(data) < 2:
        return pd.Series({
            'Mean Bias': np.nan,
            'Mean Absolute Error': np.nan,
            'RMSE': np.nan,
            'Correlation': np.nan,
            'Variance bias': np.nan
        })
    mean_bias = data['difference_interpolated'].mean()
    mean_absolute_error = data['difference_interpolated'].abs().mean()
    rmse = np.sqrt((data['difference_interpolated'] ** 2).mean())
    correlation, _ = pearsonr(data['temperature'], data['interpolated_grid_value']) # si es precipitación sustituir pearsonr por spearmanr
    variance_bias = data['temperature'].var() - data['interpolated_grid_value'].var()
    return pd.Series({
        'Mean Bias': mean_bias,
        'Mean Absolute Error': mean_absolute_error,
        'RMSE': rmse,
        'Correlation': correlation,  
        'Variance bias': variance_bias
    })

metrics_per_station_interpolated = stations_data.groupby('station_id').apply(calculate_metrics_interpolated).reset_index()

# Guardar métricas para cada estación en un csv
metrics_per_station_interpolated.to_csv('metrics_per_station_interpolated.csv', index=False)

# Imprimir métricas por cada estación 
print("Métricas usando interpolación local:")
for idx, row in metrics_per_station_interpolated.iterrows():
    print(f"Estación {row['station_id']}:")
    print(f"  Mean Bias: {row['Mean Bias']:.2f}")
    print(f"  Mean Absolute Error: {row['Mean Absolute Error']:.2f}")
    print(f"  RMSE: {row['RMSE']:.2f}")
    print(f"  Correlation: {row['Correlation']:.2f}")
    print(f"  Variance bias: {row['Variance bias']:.2f}")
    print()

# Figura con boxplots para las métricas calculadas
plt.figure(figsize=(10, 8))
sns.boxplot(data=pd.melt(metrics_per_station_interpolated, id_vars=['station_id'], value_vars=['Mean Bias', 'Mean Absolute Error', 'RMSE', 'Correlation', 'Variance bias']),
            x='variable', y='value', orient='v')
plt.xlabel('Metric')
plt.ylabel('Value')
plt.title('Boxplot of Local Interpolation Metrics per Station')
sns.despine()
plt.tight_layout()
plt.show()
evaluation_grid.py
Mostrando evaluation_grid.py.