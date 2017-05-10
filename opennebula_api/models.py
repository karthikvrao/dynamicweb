import oca
import socket

from django.db import models
from django.conf import settings

from oca.pool import WrongNameError

class VirtualMachineTemplate(models.Model):
    """This class represents an opennebula template."""
    opennebula_id = models.IntegerField()
    base_price = models.FloatField()
    memory_price = models.FloatField()
    core_price = models.FloatField()
    disk_size_price = models.FloatField()

    def calculate_price(self):
        manager = OpenNebulaManager()
        template = manger._get_template(self.opennebula_id).template

        price = int(template.vpcu) * self.core_price
        price += int(template.memory) / 1024 * self.memory_price
        try:
            price += int(template.disk.size) / 1024 * self.disk_size_price
        except AttributeError:
            for disk in template.disks:
                price += int(disk.size) / 1024 * self.disk_size_price
        return price

    def get_name(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        template = self.manager._get_template(template_id=self.opennebula_id)
        return template.name

    def get_cores(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        template = self.manager._get_template(template_id=self.opennebula_id).template
        return int(template.vcpu)
    
    def get_disk_size(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        template = self.manager._get_template(template_id=self.opennebula_id).template
        return int(template.disk.size) / 1024

    def get_memory(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        template = self.manager._get_template(template_id=self.opennebula_id).template
        return int(template.memory) / 1024

class VirtualMachine(models.Model):
    """This class represents an opennebula virtual machine."""
    opennebula_id = models.IntegerField()
    template = models.ForeignKey(VirtualMachineTemplate)

    VM_STATE = {
        '0': 'INIT',
        '1': 'PENDING',
        '2': 'HOLD',
        '3': 'ACTIVE',
        '4': 'STOPPED',
        '5': 'SUSPENDED',
        '6': 'DONE',
        '8': 'POWEROFF',
        '9': 'UNDEPLOYED',
        '10': 'CLONING',
        '11': 'CLONING_FAILURE',
    }

    def get_name(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        vm = self.manager._get_vm(vm_id=self.opennebula_id)
        return vm.name

    def get_cores(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        template = self.manager._get_vm(vm_id=self.opennebula_id).template
        return int(template.vcpu)
    
    def get_disk_size(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        template = self.manager._get_vm(vm_id=self.opennebula_id).template
        try: 
            return template.disk.size
        except AttributeError:
            disk_size = 0 
            for disk in template.disks:
                disk_size += disk.size
            return disk_size / 1024


    def get_memory(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        template = self.manager._get_vm(vm_id=self.opennebula_id).template
        return int(template.memory)

    def get_id(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        vm = self.manager._get_vm(vm_id=self.opennebula_id)
        return vm.id

    def get_ip(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        vm = self.manager._get_vm(vm_id=self.opennebula_id)
        try:
            return vm.user_template.ungleich_public_ip
        except AttributeError:
            return '-'

    def get_state(self):
        if self.manager is None:
            self.manager = OpenNebulaManager()

        vm = self.manager._get_vm(vm_id=self.opennebula_id)
        return self.VM_STATE.get(str(vm.state))

    def get_pirce(self)
        return 0.0

class OpenNebulaManager():
    """This class represents an opennebula manager."""

    def __init__(self, email=None, password=None, create_user=True):
        
        # Get oneadmin client
        self.oneadmin_client = self._get_opennebula_client(
            settings.OPENNEBULA_USERNAME,
            settings.OPENNEBULA_PASSWORD
        )
        

        if not create_user:
            return

        # Get or create oppenebula user using given credentials
        self.opennebula_user = self._get_or_create_user(
            email,
            password
        )

        # If opennebula user was created/obtained, get his client
        if self.opennebula_user:
            self.client = self._get_opennebula_client(
                email,
                password
            )

    def _get_opennebula_client(self, username, password):
        return oca.Client("{0}:{1}".format(
            username,
            password),
            "{protocol}://{domain}:{port}{endpoint}".format(
                protocol=settings.OPENNEBULA_PROTOCOL,
                domain=settings.OPENNEBULA_DOMAIN,
                port=settings.OPENNEBULA_PORT,
                endpoint=settings.OPENNEBULA_ENDPOINT
        ))

    def _get_or_create_user(self, email, password):
        try:
            user_pool = self._get_user_pool()
            opennebula_user = user_pool.get_by_name(email)
            return opennebula_user
        except WrongNameError as wrong_name_err:
            opennebula_user = self.oneadmin_client.call(oca.User.METHODS['allocate'], email,
                                                        password, 'core')
            return opennebula_user
        except ConnectionRefusedError:
            print('Could not connect to host: {host} via protocol {protocol}'.format(
                    host=settings.OPENNEBULA_DOMAIN,
                    protocol=settings.OPENNEBULA_PROTOCOL)
                )
    def _get_user_pool(self):
        try:
            user_pool = oca.UserPool(self.oneadmin_client)
            user_pool.info()
        except ConnectionRefusedError:
            print('Could not connect to host: {host} via protocol {protocol}'.format(
                    host=settings.OPENNEBULA_DOMAIN,
                    protocol=settings.OPENNEBULA_PROTOCOL)
                )
        return user_pool

    def create_virtualmachine(self, template_id):
        template_pool = oca.VmTemplatePool(self.oneadmin_client)
        template_pool.info()

        template = template_pool.get_by_id(template_id)

        vm_id = template.instantiate()
        self.oneadmin.call(
            oca.VirtualMachine.METHODS['chown'],
            vm_id,
            self.opennebula_user.id,
            self.opennebula_user.group_ids[0]
        )
        return vm_id

    def create_template(self, name, cores, memory, disk_size):
        """Create and add a new template to opennebula.
        :param name:      A string representation describing the template.
                          Used as label in view.
        :param cores:     Amount of virtual cpu cores for the VM.
        :param memory:    Amount of RAM for the VM (MB)
        :param disk_size: Amount of disk space for VM (MB)
        """
        template_string_formatter = """<TEMPLATE>
                                        <NAME>{name}</NAME>
                                        <MEMORY>{memory}</MEMORY>
                                        <VCPU>{vcpu}</VCPU>
                                        <CPU>{cpu}</CPU>
                                        <DISK>
                                         <TYPE>fs</TYPE>
                                         <SIZE>{size}</SIZE>
                                         <DEV_PREFIX>vd</DEV_PREFIX>
                                        </DISK>
                                       </TEMPLATE>
                                       """
        template_id = oca.VmTemplate.allocate(
            self.oneadmin_client,
            template_string_formatter.format(
                name=name,
                vcpu=cores,
                cpu=0.1*cores,
                size=1024 * disk_size,
                memory=1024 * memory
            )
        )

        return template_id