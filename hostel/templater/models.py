from django.template.response import SimpleTemplateResponse
from django.template.exceptions import TemplateDoesNotExist


class Templater:
    templates = {}

    class TemplaterError(Exception):
        pass

    def datacenter_disturb_message(self, datacenter):
        context = {'datacenter': datacenter}
        template_file = 'disturb_messages/datacenter.txt'
        result = self._render_template(template_file, context)
        return result

    def client_settings(self, service):

        params = service.params()

        # Checking for nets consistency
        if params['require_net'] and not service.net.all():
            return None

        context = {'service': service}
        template_file = 'client_settings/%s.txt' % service.name
        result = self._render_template(template_file, context)
        return result

    def generate_config(self, *args, **kwargs):
        service = kwargs.get('service')
        bundle = kwargs.get('bundle')

        if not any([service, bundle]):
            return None

        if service.name in ['wix', 'inet2']:
            return self.generate_config_peering(service=service, bundle=bundle)
        else:
            raise self.TemplaterError('Генерация конфига для %s не поддерживается' % service)

    def generate_config_peering(self, service=None, bundle=None):
        if not any([service, bundle]):
            return None

        if not service.net.all():
            return None

        net = None
        if service.net.all().count() == 1:
            net = service.net.first()

        template_file = 'service_config/%s_%s.txt' % (bundle.device.store_entry.vendor, service.name)
        context = {'service': service, 'bundle': bundle, 'net': net}

        result = self._render_template(template_file, context)
        return result

    def _render_template(self, template_file, context):
        try:
            t = SimpleTemplateResponse(template_file, context=context)
            t.render()
        except TemplateDoesNotExist:
            raise self.TemplaterError('Не удалось найти шаблон %s' % template_file)

        result = t.content.decode('utf-8')
        striped = ''
        for line in result.splitlines():
            if line:
                striped += line + '\n'
        return striped
