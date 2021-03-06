#!/usr/bin/env python

import urlparse
import re

import rbd
import utils

from xapi.storage import log

def _getPoolName(name):
    regex = re.compile('(.*)/(.*)')
    result = regex.match(name)
    return result.group(1)

def _getImageName(name):
    regex = re.compile('(.*)/(.*)')
    result = regex.match(name)
    return result.group(2)

def getPhysicalUtilisation(dbg, cluster, name):
    log.debug("%s: rbd_utils.getPhysicalUtilisation: Cluster ID: %s Name: %s"
              % (dbg, cluster.get_fsid(), name))

    _pool_ = _getPoolName(name)
    _image_ = _getImageName(name)
    ioctx = cluster.open_ioctx(_pool_)
    image = rbd.Image(ioctx, _image_)

    try:
        image_stat = image.stat()
        return image_stat['num_objs']*image_stat['obj_size']
        #
        #image.diff_iterate(0, image.size(), None, cb)
        #
        #return image.size()
    finally:
        ioctx.close()

def if_image_exist(dbg, cluster, name):
    log.debug("%s: rbd_utils.if_image_exist: Cluster ID: %s Image: %s"
              % (dbg, cluster.get_fsid(), name))
    _pool_ = _getPoolName(name)
    _image_ = _getImageName(name)
    ioctx = cluster.open_ioctx(_pool_)
    try:
        image = rbd.Image(ioctx, _image_)
        return True
    except Exception:
        return False

def updatePoolMetadata(dbg, cluster, _pool_, metadata):
    log.debug("%s: rbd_utils.updatePoolMeta: Cluster ID: %s Name: %s Metadata: %s "
              % (dbg, cluster.get_fsid(), _pool_, metadata))
    _image_ = utils.SR_METADATA_IMAGE_NAME
    ioctx = cluster.open_ioctx(_pool_)
    try:
        image = rbd.Image(ioctx, _image_)
    except Exception:
        create(dbg, cluster, "%s/%s" % (_pool_, _image_), 0)
        image = rbd.Image(ioctx, _image_)

    try:
        for tag, value in metadata.iteritems():
            if value is None:
                log.debug("%s: rbd_utils.updatePoolMeta: tag: %s remove value" % (dbg, tag))
                image.metadata_remove(str(tag))
            else:
                log.debug("%s: rbd_utils.updatePoolMeta: tag: %s set value: %s" % (dbg, tag, value))
                image.metadata_set(str(tag), str(value))
    finally:
        image.close()
        ioctx.close()

def retrievePoolMetadata(dbg, cluster, _pool_):
    log.debug("%s: rbd_utils.retrievePoolMeta: Cluster ID: %s Pool: %s"
              % (dbg, cluster.get_fsid(), _pool_))
    metadata = {}

    _image_ = utils.SR_METADATA_IMAGE_NAME
    ioctx = cluster.open_ioctx(_pool_)
    try:
        image = rbd.Image(ioctx, _image_)
    except Exception:
        return metadata

    try:
        return image.metadata_list()
    finally:
        image.close()
        ioctx.close()

def updateImageMetadata(dbg, cluster, name, metadata):
    log.debug("%s: rbd_utils.updateMetadata: Cluster ID: %s Name: %s Metadata: %s "
              % (dbg, cluster.get_fsid(), name, metadata))

    _pool_ = _getPoolName(name)
    _image_ = _getImageName(name)
    ioctx = cluster.open_ioctx(_pool_)
    image = rbd.Image(ioctx, _image_)

    try:
        for tag, value in metadata.iteritems():
            if value is None:
                log.debug("%s: rbd_utils.updateMetadata: tag: %s remove value" % (dbg, tag))
                image.metadata_remove(str(tag))
            else:
                log.debug("%s: rbd_utils.updateMetadata: tag: %s set value: %s" % (dbg, tag, value))
                image.metadata_set(str(tag), str(value))
    finally:
        image.close()
        ioctx.close()

def retrieveImageMetadata(dbg, cluster, image_name):
    log.debug("%s: rbd_utils.retrieveImageMeta: Cluster ID: %s Pool: %s"
              % (dbg, cluster.get_fsid(), image_name))
    _pool_ = _getPoolName(image_name)
    _image_ = _getImageName(image_name)
    ioctx = cluster.open_ioctx(_pool_)
    image = rbd.Image(ioctx, _image_)

    try:
        return image.metadata_list()
    finally:
        image.close()
        ioctx.close()

def create(dbg, cluster, name, size):
    log.debug("%s: rbd_utils.create: Cluster ID: %s Name: %s Size: %s "
              % (dbg, cluster.get_fsid(), name, size))
    _pool_ = _getPoolName(name)
    _image_ = _getImageName(name)
    ioctx = cluster.open_ioctx(_pool_)
    rbd_inst = rbd.RBD()

    try:
        rbd_inst.create(ioctx, _image_, size)
    finally:
        ioctx.close()

def snapshot(dbg, cluster, name, snap):
    log.debug("%s: rbd_utils.snapshot: Cluster ID: %s Name: %s Snap: %s "
              % (dbg, cluster.get_fsid(), name, snap))
    _pool_ = _getPoolName(name)
    _image_ = _getImageName(name)
    ioctx = cluster.open_ioctx(_pool_)
    image = rbd.Image(ioctx, _image_)

    try:
        image.create_snap(snap)
    finally:
        ioctx.close()

def clone(dbg, cluster, parent, snapshot, clone):
    log.debug("%s: rbd_utils.clone: Cluster ID: %s Parent: %s Snapshot: %s Clone: %s"
              % (dbg, cluster.get_fsid(), parent, snapshot, clone))
    p_pool = _getPoolName(parent)
    p_name = _getImageName(parent)
    p_ioctx = cluster.open_ioctx(p_pool)
    p_image = rbd.Image(p_ioctx, p_name)
    c_pool = _getPoolName(clone)
    c_name = _getImageName(clone)
    c_ioctx = cluster.open_ioctx(c_pool)
    rbd_inst = rbd.RBD()

    log.debug("%s: rbd_utils.clone: Cluster ID: %s p_pool: %s p_name: %s snap: %s c_pool: %s c_name %s"
              % (dbg, cluster.get_fsid(), p_pool, p_name, snapshot, c_pool, c_name))

    try:
        if not p_image.is_protected_snap(snapshot):
            p_image.protect_snap(snapshot)
        rbd_inst.clone(p_ioctx, p_name, snapshot, c_ioctx, c_name)
    finally:
        p_ioctx.close()
        c_ioctx.close()

def rename(dbg, cluster, old_name, new_name):
    log.debug("%s: rbd_utils.rename: Cluster ID: %s Old name: %s New name: %s"
              % (dbg, cluster.get_fsid(), old_name, new_name))
    _pool_ = _getPoolName(old_name)
    _old_image_ = _getImageName(old_name)
    _new_image_ = _getImageName(new_name)
    ioctx = cluster.open_ioctx(_pool_)
    rbd_inst = rbd.RBD()

    try:
        rbd_inst.rename(ioctx, _old_image_, _new_image_)
    finally:
        ioctx.close()

def remove(dbg, cluster, name):
    log.debug("%s: rbd_utils.remove: Cluster ID: %s Name: %s"
              % (dbg, cluster.get_fsid(), name))
    _pool_ = _getPoolName(name)
    _image_ = _getImageName(name)
    ioctx = cluster.open_ioctx(_pool_)
    rbd_inst = rbd.RBD()

    try:
        rbd_inst.remove(ioctx, _image_)
    finally:
        ioctx.close()

def resize(dbg, cluster, name, size):
    log.debug("%s: rbd_utils.resize: Cluster ID: %s Name: %s New_Size: %s "
              % (dbg, cluster.get_fsid(), name, size))
    _pool_ = _getPoolName(name)
    _image_ = _getImageName(name)
    ioctx = cluster.open_ioctx(_pool_)
    image = rbd.Image(ioctx, _image_)

    try:
        image.resize(size)
    finally:
        ioctx.close()

def list(dbg, cluster, name):
    log.debug("%s: rbd_utils.list: Cluster ID: %s"
              % (dbg, cluster.get_fsid()))
    ioctx = cluster.open_ioctx(name)
    rbd_inst = rbd.RBD()

    try:
        result = rbd_inst.list(ioctx)
        log.debug("%s: rbd_utils.list: Result: %s"
                  % (dbg, result))
        return result
    finally:
        ioctx.close()
