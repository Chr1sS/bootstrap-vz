from bootstrapvz.base import Task
from .. import phases
from ..tools import log_check_call
import apt
import filesystem
import kernel
from bootstrapvz.base.fs import partitionmaps
import os


class AddExtlinuxPackage(Task):
	description = 'Adding extlinux package'
	phase = phases.preparation
	predecessors = [apt.AddDefaultSources]

	@classmethod
	def run(cls, info):
		info.packages.add('extlinux')
		if isinstance(info.volume.partition_map, partitionmaps.gpt.GPTPartitionMap):
			info.packages.add('syslinux-common')


class ConfigureExtlinux(Task):
	description = 'Configuring extlinux'
	phase = phases.system_modification
	predecessors = [filesystem.FStab]

	@classmethod
	def run(cls, info):
		if info.release_codename == 'squeeze':
			# On squeeze /etc/default/extlinux is generated when running extlinux-update
			log_check_call(['chroot', info.root,
			                'extlinux-update'])
		from bootstrapvz.common.tools import sed_i
		extlinux_def = os.path.join(info.root, 'etc/default/extlinux')
		sed_i(extlinux_def, r'^EXTLINUX_PARAMETERS="([^"]+)"$',
		                    r'EXTLINUX_PARAMETERS="\1 console=ttyS0"')


class InstallExtlinux(Task):
	description = 'Installing extlinux'
	phase = phases.system_modification
	predecessors = [filesystem.FStab, ConfigureExtlinux]

	@classmethod
	def run(cls, info):
		if isinstance(info.volume.partition_map, partitionmaps.gpt.GPTPartitionMap):
			bootloader = '/usr/lib/syslinux/gptmbr.bin'
		else:
			bootloader = '/usr/lib/extlinux/mbr.bin'
		log_check_call(['chroot', info.root,
		                'dd', 'bs=440', 'count=1',
		                'if=' + bootloader,
		                'of=' + info.volume.device_path])
		log_check_call(['chroot', info.root,
		                'extlinux',
		                '--install', '/boot/extlinux'])
		log_check_call(['chroot', info.root,
		                'extlinux-update'])


class ConfigureExtlinuxJessie(Task):
	description = 'Configuring extlinux'
	phase = phases.system_modification

	@classmethod
	def run(cls, info):
		extlinux_path = os.path.join(info.root, 'boot/extlinux')
		os.mkdir(extlinux_path)

		from . import assets
		extlinux_assets_path = os.path.join(assets, 'extlinux')
		extlinux_tpl_path = os.path.join(extlinux_assets_path, 'extlinux.conf')
		with open(extlinux_tpl_path) as extlinux_tpl:
			extlinux_config = extlinux_tpl.read()

		root_uuid = info.volume.partition_map.root.get_uuid()
		extlinux_config = extlinux_config.format(kernel_version=info.kernel_version, UUID=root_uuid)
		extlinux_config_path = os.path.join(extlinux_path, 'extlinux.conf')
		with open(extlinux_config_path, 'w') as extlinux_conf_handle:
			extlinux_conf_handle.write(extlinux_config)
		from shutil import copy
		# Copy the boot message
		boot_txt_path = os.path.join(extlinux_assets_path, 'boot.txt')
		copy(boot_txt_path, os.path.join(extlinux_path, 'boot.txt'))


class InstallExtlinuxJessie(Task):
	description = 'Installing extlinux'
	phase = phases.system_modification
	predecessors = [filesystem.FStab, ConfigureExtlinuxJessie]
	# Make sure the kernel image is updated after we have installed the bootloader
	successors = [kernel.UpdateInitramfs]

	@classmethod
	def run(cls, info):
		if isinstance(info.volume.partition_map, partitionmaps.gpt.GPTPartitionMap):
			# Yeah, somebody saw it fit to uppercase that folder in jessie. Why? BECAUSE
			bootloader = '/usr/lib/EXTLINUX/gptmbr.bin'
		else:
			bootloader = '/usr/lib/EXTLINUX/mbr.bin'
		log_check_call(['chroot', info.root,
		                'dd', 'bs=440', 'count=1',
		                'if=' + bootloader,
		                'of=' + info.volume.device_path])
		log_check_call(['chroot', info.root,
		                'extlinux',
		                '--install', '/boot/extlinux'])
