from django.template import TemplateDoesNotExist, TemplateSyntaxError, Template, Origin
from django.template.loaders.base import Loader
from django.utils._os import safe_join
import os
import json
import pylims

class RecursiveDirectoryLoader(Loader):
    def __init__(self, engine):
        self.engine = engine
        self.template_dirs=pylims.template_dirs
    def get_template(self, template_name, skip=None):
        """
        Call self.get_template_sources() and return a Template object for
        the first template matching template_name. If skip is provided, ignore
        template origins in skip. This is used to avoid recursion during
        template extending.
        """
        tried = []
        for origin in self.get_template_sources(template_name):
            if skip is not None and origin in skip:
                tried.append((origin, "Skipped to avoid recursion"))
                continue

            try:
                contents = self.get_contents(origin)
            except TemplateDoesNotExist:
                tried.append((origin, "Source does not exist"))
                continue
            else:
                print('fetch',origin.template_name)
                return Template(
                    contents,
                    origin,
                    origin.template_name,
                    self.engine,
                )

        raise TemplateDoesNotExist(template_name, tried=tried)
    
    def get_contents(self, origin):
        try:
            with open(origin.name, encoding=self.engine.file_charset) as fp:
                return fp.read()
        except FileNotFoundError:
            raise TemplateDoesNotExist(origin)
            
    def get_template_sources(self, template_name):
        """
        An iterator that yields possible matching template paths for a
        template name.
        """ 
        
        splitname=template_name.split('/')
        if len(splitname)<2:
            return
        folderpattern=splitname[0]
        template_name=splitname[1]
        settings=json.loads(pylims.get_setup_options())
        mods = json.loads(pylims.build_module_dict())
        # print(pylims.term(),'Project:',folderpattern,'template:',template_name)
        # print(f'current mod for {folderpattern}: {settings['setup'][folderpattern]}')
        file_name = os.path.join(pylims.template_dirs,folderpattern,settings['setup'][folderpattern],template_name)
        if os.path.exists(file_name):
            name = safe_join(file_name)
            # print('\n\nLOADING TEMPLATE',name)
            yield Origin(
                    name=name,
                    template_name=template_name,
                    loader=self,
                )

    def reset(self):
        """
        Reset any state maintained by the loader instance (e.g. cached
        templates or cached loader modules).
        """
        pass