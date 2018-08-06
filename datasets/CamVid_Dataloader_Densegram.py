#!/usr/bin/env python

import torch
import random
import PIL.Image
import collections
import numpy as np
import os.path as osp
from torch.utils import data
import matplotlib.pyplot as plt


class CamVidSegDG(data.Dataset):

    class_names = np.array([
        'sky',
        'building',
        'column-pole',
        'road',
        'sidewalk',
        'tree',
        'sign',
        'fence',
        'car',
        'pedestrian',
        'bicyclist',
        'void',
    ])
    # Class weights by inferno
    class_weights = np.array([
        0.58872014284134,
        0.51052379608154,
        2.6966278553009,
        0.45021694898605,
        1.1785038709641,
        0.77028578519821,
        2.4782588481903,
        2.5273461341858,
        1.0122526884079,
        3.2375309467316,
        4.1312313079834,
        0,
    ])

    # Class weights by SegNet
    # class_weights = np.array([
    #     0.2595,
    #     0.1826,
    #     4.5640,
    #     0.1417,
    #     0.9051,
    #     0.3826,
    #     9.6446,
    #     1.8418,
    #     0.6823,
    #     6.2478,
    #     7.3614,
    #     0,
    # ])

    class_colors = np.array([
        (128, 128, 128),
        (128, 0, 0),
        (192, 192, 128),
        (128, 64, 128),
        (0, 0, 192),
        (128, 128, 0),
        (192, 128, 128),
        (64, 64, 128),
        (64, 0, 128),
        (64, 64, 0),
        (0, 128, 192),
        (0, 0, 0),
    ])
    # TODO: Provided by Inferno. Need to check if this is bgr or rgb: current is BGR
    # mean_bgr = np.array([0.4326707089857, 0.4251328133025, 0.41189489566336])*255
    # TODO: Provided by Inferno. Need to check if std is used.
    # std_bgr = np.array([0.28284674400252, 0.28506257482912, 0.27413549931506])*255
    # TODO: Provided by MeetShah. Maybe this is not correct.
    mean_bgr = np.array([104.00698793, 116.66876762, 122.67891434])
    class_ignore = 11

    def __init__(self, root, split='train', dataset='o', transform=False):
        self.root = root
        self.split = split
        self._transform = transform
        self.datasets = collections.defaultdict()
        # class 11 (the 12th class) is the ignored class
        self.n_classes = 12

        self.datasets['o'] = osp.join(self.root, 'Original_Images')
        # blur -- Gaussian
        self.datasets['bg1'] = osp.join(self.root, 'Degraded_Images', 'Blur_Gaussian', 'degraded_parameter_1')
        # blur -- motion
        self.datasets['bm1'] = osp.join(self.root, 'Degraded_Images', 'Blur_Motion', 'degraded_parameter_1')
        # haze
        self.datasets['h0.5'] = osp.join(self.root, 'Degraded_Images', 'Haze', 'degraded_parameter_0.5')
        self.datasets['h1.0'] = osp.join(self.root, 'Degraded_Images', 'Haze', 'degraded_parameter_1.0')
        self.datasets['h1.5'] = osp.join(self.root, 'Degraded_Images', 'Haze', 'degraded_parameter_1.5')
        self.datasets['h2.0'] = osp.join(self.root, 'Degraded_Images', 'Haze', 'degraded_parameter_2.0')
        self.datasets['h2.5'] = osp.join(self.root, 'Degraded_Images', 'Haze', 'degraded_parameter_2.5')
        # noise -- speckle
        self.datasets['ns1'] = osp.join(self.root, 'Degraded_Images', 'Noise_Speckle', 'degraded_parameter_1')
        # noise -- salt & pepper
        self.datasets['nsp1'] = osp.join(self.root, 'Degraded_Images', 'Noise_Salt_Pepper', 'degraded_parameter_1')

        img_o_dataset_dir = osp.join(self.root, self.datasets['o'])
        img_d_dataset_dir = osp.join(self.root, self.datasets[dataset])

        self.files = collections.defaultdict(list)
        for split in ['train', 'val']:
            imgsets_file = osp.join(root, '%s.txt' % split)
            for did in open(imgsets_file):
                did = did.strip()
                img_o_file = osp.join(img_o_dataset_dir, 'CamVid_train_images/%s.png' % did)
                img_d_file = osp.join(img_d_dataset_dir, 'CamVid_train_images/%s.png' % did)
                lbl_file = osp.join(root, 'CamVid_train_gt/%s.png' % did)
                self.files[split].append({
                    'img_o': img_o_file,
                    'img_d': img_d_file,
                    'lbl': lbl_file,
                })
        imgsets_file = osp.join(root, 'test.txt')
        for did in open(imgsets_file):
            did = did.strip()
            img_o_file = osp.join(img_o_dataset_dir, 'CamVid_test_images/%s.png' % did)
            img_d_file = osp.join(img_d_dataset_dir, 'CamVid_test_images/%s.png' % did)
            lbl_file = osp.join(root, 'CamVid_test_gt/%s.png' % did)
            self.files['test'].append({
                'img_o': img_o_file,
                'img_d': img_d_file,
                'lbl': lbl_file,
            })

    def __len__(self):
        return len(self.files[self.split])

    def __getitem__(self, index):
        data_file = self.files[self.split][index]
        # load image
        img_o_file = data_file['img_o']
        img_o = PIL.Image.open(img_o_file)
        img_o = np.array(img_o, dtype=np.uint8)
        img_d_file = data_file['img_d']
        img_d = PIL.Image.open(img_d_file)
        img_d = np.array(img_d, dtype=np.uint8)
        # load label
        lbl_file = data_file['lbl']
        lbl = PIL.Image.open(lbl_file)
        lbl = np.array(lbl, dtype=np.int32)
        lbl[lbl == 255] = -1
        if self._transform:
            return self.transform(img_o, img_d, lbl)
        else:
            return img_o, img_d, lbl

    def transform(self, img_o, img_d, lbl):
        random_crop = False
        if random_crop:
            size = (np.array(lbl.shape) * 0.8).astype(np.uint32)
            img_o, img_d, lbl = self.random_crop(img_o, img_d, lbl, size)
        random_flip = False
        if random_flip:
            img_o, img_d, lbl = self.random_flip(img_o, img_d, lbl)

        img_o = img_o[:, :, ::-1]  # RGB -> BGR
        img_o = img_o.astype(np.float64)
        img_o -= self.mean_bgr
        img_o = img_o.transpose(2, 0, 1)
        img_o = torch.from_numpy(img_o).float()

        img_d = img_d[:, :, ::-1]  # RGB -> BGR
        img_d = img_d.astype(np.float64)
        img_d -= self.mean_bgr
        img_d = img_d.transpose(2, 0, 1)
        img_d = torch.from_numpy(img_d).float()

        lbl = torch.from_numpy(lbl).long()
        return img_o, img_d, lbl

    def untransform(self, img_o, img_d, lbl):
        img_o = img_o.numpy()
        img_o = img_o.transpose(1, 2, 0)
        # img *= self.std_bgr
        img_o += self.mean_bgr
        img_o = img_o.astype(np.uint8)
        img_o = img_o[:, :, ::-1]

        img_d = img_d.numpy()
        img_d = img_d.transpose(1, 2, 0)
        # img *= self.std_bgr
        img_d += self.mean_bgr
        img_d = img_d.astype(np.uint8)
        img_d = img_d[:, :, ::-1]

        # convert to color lbl
        # lbl = self.label_to_color_image(lbl)
        lbl[lbl >= 255] = -1
        lbl[lbl < 0] = -1
        if not isinstance(lbl, np.ndarray):
            lbl = np.array(lbl)
        lbl = lbl.astype(np.uint8)
        return img_o, img_d, lbl

    def label_to_color_image(self, lbl):
        if type(lbl) is np.ndarray:
            lbl = torch.from_numpy(lbl)
        color_lbl = torch.zeros(3, lbl.size(0), lbl.size(1)).byte()
        for i, color in enumerate(self.class_colors):
            mask = lbl.eq(i)
            for j in range(3):
                color_lbl[j].masked_fill_(mask, color[j])
        color_lbl = color_lbl.numpy()
        color_lbl = np.transpose(color_lbl, (1, 2, 0))
        return color_lbl

    def random_crop(self, img_o, img_d, lbl, size):
        h, w = lbl.shape
        th, tw = size
        if w == tw and h == th:
            return img_o, img_d, lbl
        x1 = random.randint(0, w-tw)
        y1 = random.randint(0, h-th)
        img_o = img_o[y1:y1+th, x1:x1+tw, :]
        img_d = img_d[y1:y1+th, x1:x1+tw, :]
        lbl = lbl[y1:y1+th, x1:x1+tw]
        return img_o, img_d, lbl

    def random_flip(self, img_o, img_d, lbl):
        if random.random() < 0.5:
            return np.flip(img_o, 1).copy(), np.flip(img_d, 1).copy(), np.flip(lbl, 1).copy()
        return img_o, img_d, lbl


# For code testing
if __name__ == "__main__":
    root = '/home/dg/Dropbox/Datasets/CamVid'
    dataset = CamVidSegDG(root, split='train', dataset='h2.5', transform=True)
    img_o, img_d, lbl = dataset.__getitem__(1)
    img_o, img_d, lbl = dataset.untransform(img_o, img_d, lbl)
    plt.subplot(221)
    plt.imshow(img_o)
    plt.subplot(222)
    plt.imshow(img_d)
    plt.subplot(223)
    plt.imshow(lbl)
    plt.show()

    # dataset = CamVidSeg(root, split='train', dataset='o', transform=False)
    # mean_img = np.zeros((360, 480, 3))
    # for i in range(dataset.__len__()):
    #     img, lbl = dataset.__getitem__(i)
    #     mean_img += img
    # mean_img.transpose(2, 0, 1)
    # print (np.mean(mean_img[0]/dataset.__len__()))
    # print (np.mean(mean_img[1]/dataset.__len__()))
    # print (np.mean(mean_img[2]/dataset.__len__()))