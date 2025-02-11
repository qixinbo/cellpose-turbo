''' this method can become 10 times faster with cupy:
import cupy as np
from cupyx.scipy import ndimage as ndimg
'''
import numpy as np
from scipy import ndimage as ndimg

def estimate_volumes(arr, sigma=3):
    msk = arr > 50; 
    idx = np.arange(len(arr), dtype=np.uint32)
    idx, arr = idx[msk], arr[msk]
    for k in np.linspace(5, sigma, 5):
       std = arr.std()
       dif = np.abs(arr - arr.mean())
       msk = dif < std * k
       idx, arr = idx[msk], arr[msk]
    return arr.mean(), arr.std()

def flow2msk(flow_origin, prob, level=0.5, grad=0.5, area=None, volume=None):
    flow = flow_origin.copy()
    shp, dim = flow.shape[:-1], flow.ndim - 1
    l = np.linalg.norm(flow, axis=-1)
    flow = flow/l.reshape(shp+(1,))
    flow[(prob<-np.log(1/(level+1.0e-10)-1))|(l<grad)] = 0
    ss = ((slice(None),) * (dim) + ([0,-1],)) * 2
    for i in range(dim):flow[ss[dim-i:-i-2]+(i,)]=0
    sn = np.sign(flow); sn *= 0.5; flow += sn;
    dn = flow.astype(np.int32).reshape(-1, dim)
    strides = np.cumprod(np.array((1,)+shp[::-1]))
    dn = (strides[-2::-1] * dn).sum(axis=-1)
    rst = np.arange(flow.size//dim); rst += dn
    for i in range(10): rst = rst[rst]
    hist = np.bincount(rst, None, len(rst))
    hist = hist.astype(np.uint32).reshape(shp)
    lab, n = ndimg.label(hist, np.ones((3,)*dim))
    volumes = ndimg.sum(hist, lab, np.arange(n+1))
    areas = np.bincount(lab.ravel())
    mean, std = estimate_volumes(volumes, 2)
    if volume is None: volume = max(mean-std*3, 50)
    if area is None: area = volumes // 3
    msk = (areas<area) & (volumes>volume)
    lut = np.zeros(n+1, np.uint32)
    lut[msk] = np.arange(1, msk.sum()+1)
    mask = lut[lab].ravel()[rst].reshape(shp)
    return hist, lut[lab], mask

if __name__ == '__main__':
    from skimage.io import imread, imsave
    from skimage.data import coins, gravel
    from skimage.segmentation import find_boundaries
    
    import matplotlib.pyplot as plt
    from time import time

    import cellpose
    from cellpose import models, utils

    img = gravel()
    use_GPU = models.use_gpu()
    model = models.Cellpose(gpu=use_GPU, model_type='cyto')
    channels = [0, 0]
    mask, flow, style, diam = model.eval(
        img, diameter=30, rescale=None, channels=[0,0])
    start = time()
    water, core, msk = flow2msk(flow[1].transpose(1,2,0), flow[2])
    print('flow to mask cost:', time()-start)
    ax1, ax2, ax3, ax4, ax5, ax6 =\
        [plt.subplot(230+i) for i in (1,2,3,4,5,6)]
    ax1.imshow(img)
    ax2.imshow(flow[0])
    ax3.imshow(np.log(water+1))
    ax4.imshow(core)
    ax5.imshow(msk)
    ax6.imshow(~find_boundaries(msk)*img)
    plt.show()
