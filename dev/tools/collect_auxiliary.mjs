/* Public COG subsets only; no Earthdata credential, no full global tile download. */
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {fromUrl} from 'geotiff';

const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../..');
const sources={
 dem_source_crop:'https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N16_00_E107_00_DEM/Copernicus_DSM_COG_10_N16_00_E107_00_DEM.tif',
 jrc_source_crop:'https://s3.waw4-1.cloudferro.com/swift/v1/global-surface-water/download2024/Aggregated/VER1-5/occurrence/occurrence_100E_20N_v1_5_2024.tif'
};
for(const [name,url] of Object.entries(sources)){
 const tiff=await fromUrl(url),image=await tiff.getImage();
 const origin=image.getOrigin(),resolution=image.getResolution();
 const window=[Math.floor((107.44-origin[0])/resolution[0]),Math.floor((16.61-origin[1])/resolution[1]),Math.ceil((107.76-origin[0])/resolution[0]),Math.ceil((16.29-origin[1])/resolution[1])];
 const values=await image.readRasters({window,samples:[0],interleave:true,pool:null});
 const point=image.getGeoKeys().GTRasterTypeGeoKey===2,offset=point ? 0.5 : 0;
 const transform=[resolution[0],0,origin[0]+(window[0]-offset)*resolution[0],0,resolution[1],origin[1]+(window[1]-offset)*resolution[1]];
 const meta={source:url,window,width:window[2]-window[0],height:window[3]-window[1],dtype:values.constructor.name,transform,crs:'EPSG:4326',nodata:image.getGDALNoData(),retrieved_at:new Date().toISOString(),pixel_registration:point?'Source PixelIsPoint converted to outer-corner affine.':'Source PixelIsArea.'};
 const base=path.join(root,'data','auxiliary',name);await fs.mkdir(path.dirname(base),{recursive:true});
 await fs.writeFile(base+'.bin',new Uint8Array(values.buffer,values.byteOffset,values.byteLength));
 await fs.writeFile(base+'.json',JSON.stringify(meta,null,2));
 console.log(name,meta.width,meta.height,'saved');
}
