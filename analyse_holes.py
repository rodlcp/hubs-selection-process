import pandas as pd
import numpy as np
import json

# load data
data = pd.read_parquet('2023 DE_case_dataset.gz.parquet')

# parse json string into dict
data['holes'] = data['holes'].map(json.loads, na_action = 'ignore')

# create DataFrame with each hole as a row
holes = pd.DataFrame(
    data[['uuid', 'created', 'units', 'holes']]
    .explode('holes')
    .dropna()
)

# extract length and radius for each hole
holes['length'] = holes['holes'].map(lambda x: x['length'])
holes['radius'] = holes['holes'].map(lambda x: x['radius'])
holes['ratio'] = holes['length'] / holes['radius']

# verify critical conditions for each hole
holes['has_unreachable_hole_warning'] = holes['ratio'] > 20
holes['has_unreachable_hole_error'] = holes['ratio'] > 80

# analyse holes by each object
holes_by_object = (
    holes
    .groupby('uuid')
    .agg({
        'holes': 'count',
        'has_unreachable_hole_warning': ['any', 'sum'],
        'has_unreachable_hole_error': ['any', 'sum'],
    })
)

holes_by_object.columns = [
    'holes_amount',
    'has_unreachable_hole_warning',
    'amount_unreachable_hole_warning',
    'has_unreachable_hole_error',
    'amount_unreachable_hole_error',
]


# complete the original data with the required columns
data = pd.merge(
    data,
    holes_by_object[['has_unreachable_hole_warning', 'has_unreachable_hole_error']],
    how = 'left',
    left_on = 'uuid', 
    right_index = True
)

# save final DataFrame
data.to_parquet('output.gz.parquet', compression = 'gzip')


# generating insights

## structure and size
# df with correct column types
correct_type = pd.DataFrame(
    {'correct_type': ['datetime', 'datetime', 'datetime', 'object', 'object','object', 'object', 'object', 'object','object', 'object', 'object', 'object','float', 'string', 'string', 'float', 'string']},
    index = ['created', 'updated', 'queued', 'geometric_heuristics', 'holes', 'job_run_time', 'latheability', 'machining_directions', 'multipart', 'neighbors', 'poles', 'sheet_like_shape', 'unmachinable_edges', 'extrusion_height', 'units', 'status', 'time', 'uuid']
)

# get info df
info = pd.DataFrame(data.count(), columns = ['non-null_count'])
info.drop(index = ['has_unreachable_hole_warning', 'has_unreachable_hole_error'])
info['original_type'] = data.dtypes
info = pd.merge(info, correct_type, left_index = True, right_index = True)

## summary with general amounts and informations about the holes
summary_dicts = {
    'objects':{
        'Total objects': data.shape[0],
        'Objects with holes': holes_by_object.shape[0],
        'Objects with poor ratio holes': holes_by_object['has_unreachable_hole_warning'].sum(),
        'Objects with 2 or more poor ratio holes': (holes_by_object['amount_unreachable_hole_warning'] > 1).sum(),
        'Objects with critical ratio holes': holes_by_object['has_unreachable_hole_error'].sum(),
        'Objects with 2 or more critical ratio holes': (holes_by_object['amount_unreachable_hole_error'] > 1).sum()
    }, 
    'holes': {
        'Total holes': holes.shape[0],
        'Holes with poor ratio': holes['has_unreachable_hole_warning'].sum(),
        'Holes with critical ratio': holes['has_unreachable_hole_error'].sum(),
    }
}

# calculating absolute and percentage values for each row
summary_dfs = {i: pd.DataFrame({
    "absolute_counts": summary_dicts[i].values()
}, index = summary_dicts[i].keys()) for i in summary_dicts}

summary_dfs['objects']['percentage'] = summary_dfs['objects']['absolute_counts'] / data.shape[0]
summary_dfs['holes']['percentage'] = summary_dfs['holes']['absolute_counts'] / holes.shape[0]

# final summary df
summary = pd.concat(summary_dfs.values())

## evaluating simple distributions of data regarding holes

# ensuring that every hole is in the same unit
def get_conversion(unit):
    if unit == 'mm':
        return 1.
    elif unit == 'in':
        return 25.4
    elif unit == 'cm':
        return 10.
    else:
        raise Exception(f"Conversion from {unit} to mm is not implemented")

holes['conversion'] = holes['units'].map(get_conversion)

holes['length'] *= holes['conversion']
holes['radius'] *= holes['conversion']

# calculating hole volume
holes['volume'] = np.pi * holes['radius'] ** 2 * holes['length']

holes.drop(columns = ['units', 'conversion'], inplace = True)

# function to get general metrics (mean, std and quantiles) for each column within a DataFrame
def get_distributions(df, columns, quantiles = [0.0, 0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99, 1.]):
    distribution_values = np.zeros((len(quantiles) + 2, len(columns)))

    distribution_values[0] = df[columns].mean()
    distribution_values[1] = df[columns].std()

    for i, q in enumerate(quantiles):
        distribution_values[i + 2] = df[columns].quantile(q)
    
    distribution = pd.DataFrame(distribution_values, columns = columns)

    distribution.index = ['mean', 'std'] + [f"{100 * i:.0f}%" for i in quantiles]
    distribution.rename(index = {
        '0%': 'min',
        '100%': 'max',
    }, inplace = True)
    return distribution

# evaluating the metrics for interesting columns
distribution_df1 = get_distributions(holes, ['length', 'radius', 'volume', 'ratio'])
distribution_df2 = get_distributions(holes_by_object, ['holes_amount', 'amount_unreachable_hole_warning', 'amount_unreachable_hole_error'])

# final distribution DataFrame
distribution = pd.merge(distribution_df1, distribution_df2, left_index = True, right_index = True)
distribution.rename(columns = {
    'length': 'length (mm)',
    'radius': 'radius (mm)',
    'volume': 'volume (mm³)',
}, inplace = True)


## saving all findings in a simple formatted Excel
with pd.ExcelWriter('basic_insights.xlsx') as writer:
    info.to_excel(writer, sheet_name = 'General Info')
    summary.to_excel(writer, sheet_name = 'Summary')
    distribution.to_excel(writer, sheet_name = 'Distrbutions (obj. with holes)')
    
    workbook  = writer.book
    
    percentage_format = workbook.add_format({'num_format': '0%'})
    int_format = workbook.add_format({'num_format': '#,##0'})
    float_format = workbook.add_format({'num_format': '#,##0.00'})
    
    info_worksheet = writer.sheets['General Info']
    
    info_worksheet.set_column(0, 0, 20)
    info_worksheet.set_column(1, 1, 14, int_format)
    info_worksheet.set_column(2, 3, 12)
       
    summary_worksheet = writer.sheets['Summary']
    
    summary_worksheet.set_column(0, 0, 38)
    summary_worksheet.set_column(1, 1, 16, int_format)
    summary_worksheet.set_column(2, 2, 12, percentage_format)
    
    distribution_worksheet = writer.sheets['Distrbutions (obj. with holes)']
    
    distribution_worksheet.set_column(0, 0, 8)
    distribution_worksheet.set_column(1, 3, 12, int_format)
    distribution_worksheet.set_column(4, 4, 8, float_format)
    distribution_worksheet.set_column(5, 5, 14, int_format)
    distribution_worksheet.set_column(6, 7, 14, float_format)