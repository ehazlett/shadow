#!/usr/bin/env python
#
#

import os
import subprocess
from datetime import date, datetime
import shutil
import logging
import commands
import tempfile

__AUTHOR__ = 'Evan Hazlett <ejhazlett@gmail.com>'
__VERSION__ = '0.34'

def find_os_version():
    os_ver = platform.linux_distribution()
    if os_ver[0] != '':
        return os_ver
    if os.path.exists('/etc/arch-release'):
        kernel_ver = platform.uname()[2]
        return ('ArchLinux', kernel_ver, '')

class Shadow(object):
    def __init__(self, rootfs_dir='/', kernel_dir='/boot', snapshot_dir='/.shadow', debug=False):
        self.log = logging.getLogger('shadow')
        self._kernel_dir = kernel_dir
        self._rootfs_dir = rootfs_dir
        self._snap_dir = snapshot_dir
        self._snapshots = None
        if debug:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)
        if not os.path.exists(self._snap_dir):
            os.makedirs(self._snap_dir)
        # gather snapshots
        self._gather_snapshots()

    def get_snapshots(self):
        self.log.debug('Getting snapshots from {0}'.format(self._snap_dir))
        return self._gather_snapshots()
        
    def _check_root_filesystem(self):
        """
        Checks root filesystem for compatibility

        :rtype boolean:

        """
        mounts = commands.getoutput('mount').split('\n')
        for m in mounts:
            if m.find(' / ') > -1:
                root_fs = m
        if root_fs.find('btrfs') > -1:
            self.log.debug('Found btrfs filesystem on {0}'.format(root_fs))
            return True
        else:
            self.log.error('Only root filesystems on btrfs are supported')
            return False

    def _find_btrfs_vol_id(self, snapshot_id):
        # don't lookup default (root) subvolume; simply return
        if snapshot_id == 0 or snapshot_id == '0':
            return 0
        vols = commands.getoutput('btrfs subvolume list {0}'.format(self._rootfs_dir)).split('\n')
        for v in vols:
            if v.find(snapshot_id) > -1:
                return v.split()[1]
        return None

    def _gather_snapshots(self):
        if os.path.exists(self._snap_dir):
            self._snapshots = os.listdir(self._snap_dir)
        return self._snapshots

    @staticmethod
    def _get_timestamp():
        return datetime.strftime(datetime.now(), '%Y%m%d%H%M')

    def clear_snapshots(self):
        for s in self._snapshots:
            self.log.debug('Removing snapshot {0} from {1}'.format(s, self._snap_dir))
            p = subprocess.Popen(['btrfs subvolume delete {0} 2>&1 > /dev/null'.format(os.path.join(self._snap_dir, s))], shell=True)
            p.wait()
            self.log.debug('Removing kernel/initrd snapshot for {0}'.format(s))
            p = subprocess.Popen(['find {0} -name "*{1}" -delete'.format(self._kernel_dir, s)], shell=True)
            p.wait()
        self._gather_snapshots()
        self.log.info('Snapshots cleared')

    def remove_snapshot(self, snapshot_id=None):
        """
        Removes specified snapshot

        """
        if os.path.exists(os.path.join(self._snap_dir, snapshot_id)):
            self.log.info('Removing snapshot {0} from {1}'.format(snapshot_id, self._snap_dir))
            p = subprocess.Popen(['btrfs subvolume delete {0} 2>&1 > /dev/null'.format(os.path.join(self._snap_dir, snapshot_id))], shell=True)
            p.wait()
        kernel_found = False
        for k in os.listdir(self._kernel_dir):
            if snapshot_id in k:
                kernel_found = True
                break
        if kernel_found:
            self.log.info('Removing kernel/initrd snapshot for {0}'.format(snapshot_id))
            p = subprocess.Popen(['find {0} -name "*{1}" -delete'.format(self._kernel_dir, snapshot_id)], shell=True)
            p.wait()

    def _mount_vol(self, vol=None, vol_id=None, path=None):
        """
        Mounts a subvolume at the specified path

        """
        if not vol or vol_id == None or not path:
            self.log.error('You must specify a vol, vol_id, and path')
            return
        p = subprocess.Popen(['mount -t btrfs -o subvolid={0} {1} {2}'.format(vol_id, vol, path)], shell=True)
        p.wait()

    def _unmount_vol(self, path=None):
        """
        Unmounts the volume at the specified path

        """
        if not path:
            self.log.error('You must specify a path to unmount')
            return False
        # unmount and cleanup
        p = subprocess.Popen(['umount {0}'.format(path)], shell=True)
        ret_code = p.wait()
        if ret_code != 0:
            self.log.warn('Unable to unmount {0}'.format(path))
            return False
        else:
            return True

    def _find_root_dev(self):
        """
        Finds corresponding root device for root fs mount

        """
        mounts = commands.getoutput('mount').split('\n')
        rootfs_mount = None
        for m in mounts:
            if m.find(' / ') > -1:
                rootfs_mount = m
                break
        if not rootfs_mount:
            # unable to find mount
            return None
        root_dev = rootfs_mount.split()[0]
        # check for 'mount-by-disk-label'
        if root_dev.find('[') > -1:
            root_dev = root_dev.split('[')[0]
        return root_dev

    def activate_snapshot(self, snapshot_id=None):
        """
        Activates a snapshot for next boot

        """
        if snapshot_id == 0:
            # boot default (root) subvolume
            root_dev = self._find_root_dev()
            if not root_dev:
                self.log.error('Unable to find root device.  Cannot activate default snapshot.')
                return
            # mount default subvolume to a temp location to activate volume
            tmp_dir = tempfile.mkdtemp()
            self._mount_vol(vol=root_dev, vol_id=0, path=tmp_dir)
            # activate default volume
            p = subprocess.Popen(['btrfs subvolume set-default 0 {0}'.format(tmp_dir)], shell=True)
            p.wait()
            # unmount and cleanup
            if self._unmount_vol(tmp_dir):
                shutil.rmtree(tmp_dir)
            # TODO: revert to 'default' kernel? how to track?
            self.log.info('Default subvolume set as active.  Reboot to activate.')
            return
        snapshot_found = False
        if os.path.exists(os.path.join(self._snap_dir, snapshot_id)):
            snapshot_found = True
            vol_id = self._find_btrfs_vol_id(snapshot_id)
            if not vol_id:
                self.log.error('Unable to find snapshot.  Make sure you are not currently running in a snapshot.')
                return
            self.log.debug('Activating snapshot {0} from {1}'.format(snapshot_id, self._snap_dir[1:]))
            p = subprocess.Popen(['btrfs subvolume set-default {0} {1} 2>&1 > /dev/null'.format(vol_id, self._rootfs_dir)], shell=True)
            p.wait()
        kernel_found = False
        for k in os.listdir(self._kernel_dir):
            if snapshot_id in k:
                kernel_found = True
                break
        if kernel_found:
            self.log.debug('Activating kernel/initrd snapshot for {0}'.format(snapshot_id))
            for f in os.listdir(self._kernel_dir):
                if f.find(snapshot_id) > -1:
                    shutil.copy(os.path.join(self._kernel_dir, f), os.path.join(self._kernel_dir, '{0}'.format(f.replace('.{0}'.format(snapshot_id), ''))))
        if snapshot_found:
            self.log.info('Snapshot {0} set as default.  Reboot to activate.'.format(snapshot_id))

    def merge_snapshot(self, source_snapshot=None, target_snapshot=None):
        """
        Merges two snapshots

        """
        if not source_snapshot or not target_snapshot:
            self.log.error('You must specify a source_snapshot and target_snapshot')
            return
        # create dirs for mounts
        source_tmp = tempfile.mkdtemp()
        target_tmp = tempfile.mkdtemp()
        root_dev = self._find_root_dev()
        if not root_dev:
            self.log.error('Unable to find root device.  Cannot merge snapshots.')
            return
        source_vol_id = self._find_btrfs_vol_id(source_snapshot)
        self.log.debug('Source vol ID: {0}'.format(source_vol_id))
        target_vol_id = self._find_btrfs_vol_id(target_snapshot)
        self.log.debug('Target vol ID: {0}'.format(target_vol_id))
        self._mount_vol(vol=root_dev, vol_id=source_vol_id, path=source_tmp)
        self._mount_vol(vol=root_dev, vol_id=target_vol_id, path=target_tmp)
        # merge
        self.log.info('Merging {0} with {1}...'.format(source_snapshot, target_snapshot))
        p = subprocess.Popen(['rsync -rlptgoxDEXA --exclude="/tmp*" --exclude="/proc/*" --exclude="/sys/*" --exclude="/dev/*" {0}/ {1}/'.format(source_tmp, target_tmp)], shell=True)
        p.wait()
        self._unmount_vol(source_tmp)
        self._unmount_vol(target_tmp)
        self.log.info('Merging complete')

    def _snap_kernels(self, name=None):
        """
        Takes a snapshot of the system kernels and ramdisks

        """
        if not name:
            name = self._get_timestamp()
        snaps = self.get_snapshots()
        #[shutil.copy(os.path.join(self._kernel_dir, k), os.path.join(self._kernel_dir, '{0}.{1}'.format(k, timestamp)))\
        #    for k in os.listdir(self._kernel_dir) if k.split('.')[-1] not in snaps and k.find('kernel') > -1 or k.find('vmlinuz') > -1\
        #    or k.find('initrd') > -1]
        for k in os.listdir(self._kernel_dir):
            # find kernels
            snap_exists = False
            for s in snaps:
                if k.find(s) > -1:
                    snap_exists = True
                    break
            if not snap_exists:
                if k.find('kernel') > -1 or k.find('vmlinuz') > -1 or k.find('initrd') > -1:
                    # filter existing snapshots -- if snapshot is created immediately after another
                    if k.find(name) == -1:
                        self.log.debug('Creating snapshot for kernel or initrd: {0}.{1}'.format(k, name))
                        shutil.copy(os.path.join(self._kernel_dir, k), os.path.join(self._kernel_dir, '{0}.{1}'.format(k, name)))

    def _snap_rootfs(self, name=None):
        """
        Takes a snapshot of the root filesystem (if supported)

        """
        if not name:
            name = self._get_timestamp()
        if self._check_root_filesystem():
            cmd = 'btrfs subvolume snapshot {0} {1}/{2} 2>&1 > /dev/null'.format(self._rootfs_dir, self._snap_dir, name)
            p = subprocess.Popen([cmd], shell=True)
            ret_code = p.wait()
            if ret_code != 0:
                self.log.error('Error creating root fs snapshot.  Check syslog')
            else:
                self.log.debug('Creating snapshot for root fs: {0}'.format(name))

    def take_snapshot(self, name=None):
        """
        Takes a system snapshot (kernels and root fs)

        """
        if not name:
            name = self._get_timestamp()
        # snapshot kernels/initrds
        self._snap_kernels(name=name)
        # snapshot root fs (/)
        self._snap_rootfs(name=name)
        # reload snapshots
        self._gather_snapshots()
        self.log.info('Created snapshot {0}'.format(name))
        return (name, datetime.now().isoformat()) 

