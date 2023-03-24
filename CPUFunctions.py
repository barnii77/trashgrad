import numpy as np
from scipy import signal


def correlate_kernels(volumes, kernels, mode="valid", remove_input_depth_dimension=True):
    """volumes = images"""
    assert len(volumes.shape) == len(kernels.shape)
    if mode == "valid":
        x = np.empty((kernels.shape[0], volumes.shape[0],
                      *(volumes.shape[i] - kernels.shape[i] + 1 for i in range(1, len(volumes.shape)))))
    elif mode == "full":
        x = np.empty((kernels.shape[0], volumes.shape[0],
                      *(volumes.shape[i] + kernels.shape[i] - 1 for i in range(1, len(volumes.shape)))))
    else:
        raise Exception(f"mode {mode} is not a valid mode for cross-correlation (valid modes are 'valid' & 'full')")

    for i, k in enumerate(kernels):
        x[i] = signal.correlate(volumes, k.reshape((1, *k.shape)), mode)

    if remove_input_depth_dimension:
        x = x.reshape((*x.shape[:2], *x.shape[3:]))
    x = np.transpose(x, (1, 0, *range(2, len(volumes.shape))))
    return x


def correlate_batches(volumes, kernels, mode="valid"):
    # batch size needs to be the same
    assert len(volumes.shape) == len(kernels.shape) and volumes.shape[0] == kernels.shape[0]
    if mode == "valid":
        x = np.empty((volumes.shape[0],
                      *(volumes.shape[i] - kernels.shape[i] + 1 for i in range(1, len(volumes.shape)))))
    elif mode == "full":
        x = np.empty((volumes.shape[0],
                      *(volumes.shape[i] + kernels.shape[i] - 1 for i in range(1, len(volumes.shape)))))
    else:
        raise Exception(f"mode {mode} is not a valid mode for cross-correlation (valid = 'valid' & 'full')")

    for i in range(volumes.shape[0]):  # for sample in batch
        x[i] = signal.correlate(volumes[i], kernels[i], mode)

    return x


def correlate_kernels_loop(volumes, kernels, mode="valid", remove_input_depth_dimension=True):
    """volumes = images"""
    assert len(volumes.shape) == len(kernels.shape)
    x = np.empty((volumes.shape[0], kernels.shape[0],
                  *(volumes.shape[i] - kernels.shape[i] + 1 for i in range(1, len(volumes.shape)))))

    for i in range(volumes.shape[0]):
        for j in range(kernels.shape[0]):
            x[i, j] = signal.correlate(volumes[i], kernels[j], mode)

    if remove_input_depth_dimension:
        x = x.reshape((*x.shape[:2], *x.shape[3:]))
    return x


def convolve_equal_depth_loop(volumes, kernels, mode="full"):
    """volumes = gradient"""
    assert len(kernels.shape) == len(volumes.shape)
    x = np.zeros((volumes.shape[0], kernels.shape[1],
                  *(volumes.shape[i] + kernels.shape[i] - 1 for i in range(2, len(kernels.shape)))))

    for i in range(volumes.shape[0]):  # for sample in batch
        for j in range(kernels.shape[1]):  # for layer in image_depth
            for k in range(kernels.shape[0]):  # for kernel in kernels (gradient.shape[1] == kernels.shape[0] == depth)
                x[i, j] += signal.convolve(volumes[i, k], kernels[k, j], mode)

    return x


def concat(*tensors, axis=0):
    return tensors[0].concat(*tensors[1:], axis=axis)


def pool(data, sizes, criterion, criterion_included):
    out = np.empty((data.shape[0], data.shape[1], *(dim // sizes[i] for i, dim in enumerate(data.shape[2:]))))
    out_grad = []  # np.zeros(data.shape)

    def _f(subarr):
        ret = np.zeros(subarr.shape)
        indeces = criterion_included(subarr)
        if isinstance(indeces, int):
            indeces = (indeces,)
        for idx in indeces:
            ret[np.unravel_index(idx, ret.shape)] = 1
        return ret

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            subarrays = np.split(data[i, j], data.shape[2] // sizes[0], 0)
            for axis in range(1, len(data.shape) - 2):
                new_subarrays = []
                for ary in subarrays:
                    new_subarrays.extend(np.split(ary.data, ary.shape[axis] // sizes[axis], axis))
                subarrays = new_subarrays
            res = np.array([criterion(subarr) for subarr in subarrays])
            for subarr in subarrays:
                out_grad.append(_f(subarr))  # included.reshape(data.shape[2:])
            out[i, j] = res.reshape([dim // sizes[i] for i, dim in enumerate(data.shape[2:])])
    return out, np.array(out_grad)


def averagepool(data, sizes, *_):
    out = np.empty((data.shape[0], data.shape[1], *(dim // sizes[i] for i, dim in enumerate(data.shape[2:]))))
    out_grad = []  # np.zeros(data.shape)

    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            subarrays = np.split(data[i, j], data.shape[2] // sizes[0], 0)
            for axis in range(1, len(data.shape) - 2):
                new_subarrays = []
                for ary in subarrays:
                    new_subarrays.extend(np.split(ary.data, ary.shape[axis] // sizes[axis], axis))
                subarrays = new_subarrays
            res = np.array([np.average(subarr) for subarr in subarrays])
            for subarr in subarrays:
                out_grad.append(np.ones(subarr.shape))  # included.reshape(data.shape[2:])
            out[i, j] = res.reshape([dim // sizes[i] for i, dim in enumerate(data.shape[2:])])
    return out, np.array(out_grad)