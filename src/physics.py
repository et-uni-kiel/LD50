# -*- coding: utf-8 -*-
"""
Created on Sun Jun 01 11:24:13 2014

@author: koehler
"""
#constants
from scipy.constants import \
    atomic_mass as amu,\
    e as q_e, \
    pi, \
    m_e, \
    c as c_light,\
    epsilon_0,\
    N_A
from scipy.constants import physical_constants
m_muon = physical_constants['muon mass'][0]

#Units
um = 1e-6
mm = 1e-3
cm = 1e-2
m = 1
km = 1e3

cm2 = 1e-4
cm3 = 1e-6
m3 = 1

g = 1e-3
kg = 1

eV = q_e
keV = q_e*1e3
MeV = q_e*1e6

deg = 2*pi/360

barn = 1e-28

def quality_factor(L):
    """
    Quality factor according to wikipedia
    """
    from numpy import sqrt
    L /= (keV/um)
    if L < 10:
        return 1
    elif L < 100:
        return 0.32*L-2.2
    else:
        return 300./sqrt(L)


class Volume(object):
    def __init__(self, fn_image, name, material, s2px=1e3):
        from scipy.misc import imread
        self.fn_image = fn_image
        self.image = imread(fn_image)
        self.name = name
        self.s2px = s2px
        self.material = material
        self._set_bbox()
    def is_inside(self, pos_x, pos_y):
        """ """
        x0, y0, x1, y1 = self.bbox
        if (x0 <= pos_x < x1) and (y0 <= pos_y < y1):
            pos_x = int(pos_x*self.s2px)
            pos_y = int(pos_y*self.s2px)
            if self.image[-pos_y][pos_x][3]>0:
                return True
        else:
            return False
    def get_mexpot_edens(self, pos_x, pos_y):
        """
        Returns a tuple o the
        means excitation potential and the electron density
        """
        if self.is_inside(pos_x, pos_y):
            return self.material.get_mean_ex_pot(), self.material.get_e_density()
        else:
            return 1e-30, 0
    def get_neutron_mfp(self, pos_x, pos_y, energy):
        """
        Returns the mean free path for neutrons
        """
        if self.is_inside(pos_x, pos_y):
            return self.material.get_neutron_mfp(energy)
        else:
            return []
    def get_gamma_mfp(self, pos_x, pos_y, energy):
        """
        Returns the mean free path for neutrons
        """
        if self.is_inside(pos_x, pos_y):
            return self.material.get_gamma_mfp(energy)
        else:
            return []
    def _set_bbox(self):
        self.bbox =  (0, #x0
                      0, #y0
                      self.image.shape[1]/self.s2px,  #x1
                      self.image.shape[0]/self.s2px) #y1
    def is_in_bbox(self, pos_x, pos_y):
        x0, y0, x1, y1 = self.bbox
        if (x0 <= pos_x <= x1) and (y0 <= pos_y <= y1):
            return True
        else:
            return False

    def get_image_info(self):
        """
        Returns a list of [[image fn, scaling factor, offset]]
        """
        return [[self.fn_image, self.bbox]]
    def get_name(self):
        return [self.name]


class MotherVolume(Volume):
    """
    Manages a list of volumes.

    Args:
    -----
    volumes : list
        list of Volume class objects (default=[])
    offsets : list
        list of (x,y) position offset of the corresponding volumes (default=[])
        If [] is supplied, (0,0) is assumed for every Volume

    If there are overlaps between different volumes, the last volume in the
    list is used.

    Note:
    -----
    MotherVolumes can contain MotherVolumes
    """
    def __init__(self, volumes=[], offsets=[]):
        import numpy
        self.volumes = volumes
        if offsets == []:
            offsets = [(0,0) for i in xrange(len(volumes))]
        self.offsets = numpy.array(offsets)
        self._set_bbox()
    def add_volume(self, volume, offset=(0,0)):
        """
        Add another voume, offset pair to the mothervolume
        """
        self.volumes.append(volume)
        self.offsets.append(offset)
        self._set_bbox()
    def get_volume(self, pos_x, pos_y):
        for i in xrange(1, len(self.volumes)+1):
            x0, y0 = self.offsets[-i]
            if self.volumes[-i].is_inside(pos_x-x0, pos_y-y0):
                return self.volumes[-i]
        return None
    def is_inside(self, pos_x, pos_y):
        for i in xrange(1, len(self.volumes)+1):
            x0, y0 = self.offsets[-i]
            if self.volumes[-i].is_inside(pos_x-x0, pos_y-y0):
                return True
        return False
    def get_mexpot_edens(self, pos_x, pos_y):
        """
        Returns a tuple o the
        means excitation potential and the electron density
        """
        volume = self.get_volume(pos_x, pos_y)
        if volume:
            return volume.get_mexpot_edens(pos_x, pos_y)
        return 1e-30, 0

    def get_neutron_mfp(self, pos_x, pos_y, energy):
        """
        Returns the mean free path for neutrons
        """
        volume = self.get_volume(pos_x, pos_y)
        if volume:
            return volume.material.get_neutron_mfp(energy)
        else:
            return []
    def get_gamma_mfp(self, pos_x, pos_y, energy):
        """
        Returns the mean free path for neutrons
        """
        volume = self.get_volume(pos_x, pos_y)
        if volume:
            return volume.material.get_gamma_mfp(energy)
        else:
            return []

    def get_image_info(self):
        """
        Returns a list of [image fn, bbox] for each volume
        """
        im_info = []
        for i in xrange(len(self.volumes)):
            for fn, bbox in self.volumes[i].get_image_info():
                x0, y0, x1, y1 = bbox
                dx, dy = self.offsets[i]
                im_info.append([fn, (x0+dx, y0+dy, x1+dx, y1+dy)])
        return im_info

    def _set_bbox(self):
        """
        Returns the smallest bbox containing all volumes
        """
        from numpy import array
        bboxes = []
        for i in xrange(len(self.volumes)):
            x0, y0, x1, y1 = self.volumes[i].bbox
            dx, dy = self.offsets[i]
            bboxes.append((x0+dx, y0+dy, x1+dx, y1+dy))
        bboxes = array(bboxes)
        self.bbox = (bboxes[:,0].min(), bboxes[:,1].min(),  #x0, y0
                     bboxes[:,2].max(), bboxes[:,3].max()) #x1, y1

    def get_name(self):
        """
        Returns a list of names for all volumes
        """
        names = []
        for volume in self.volumes:
            names += volume.get_name()
        return names
            

