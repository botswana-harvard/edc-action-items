from django.apps import apps as django_apps
from django.core.exceptions import ObjectDoesNotExist
from urllib.parse import urlencode, unquote
from edc_constants.constants import CLOSED, NEW, OPEN

from ..site_action_items import site_action_items
from .action_item_getter import ActionItemGetter, ActionItemObjectDoesNotExist


class ActionError(Exception):
    pass


class ReferenceModelObjectDoesNotExist(ObjectDoesNotExist):
    pass


class Action:

    action_item_getter = ActionItemGetter

    _updated_action_type = False

    admin_site_name = None
    color_style = 'danger'
    create_by_action = None
    create_by_user = None
    display_name = None
    help_text = None
    instructions = None
    name = None
    parent_reference_model_fk_attr = None
    priority = None
    reference_model = None
    show_link_to_add = False
    show_link_to_changelist = False
    show_on_dashboard = None
    singleton = False

    action_type_model = 'edc_action_item.actiontype'
    next_actions = None  # a list of Action classes which may include 'self'

    def __init__(self, subject_identifier=None, action_identifier=None,
                 reference_identifier=None, parent_reference_identifier=None,
                 reference_model_obj=None):

        self.action_item_obj = None

        self.action_registered_or_raise()

        if reference_model_obj:
            if reference_model_obj._meta.label_lower != self.reference_model.lower():
                raise ActionError(
                    f'Invalid model for {repr(self)}. Expected {self.reference_model}. '
                    f'Got \'{reference_model_obj._meta.label_lower}\'.')
            self.action_identifier = reference_model_obj.action_identifier
            self.subject_identifier = reference_model_obj.subject_identifier
            self.reference_identifier = reference_model_obj.tracking_identifier
            self.parent_reference_identifier = reference_model_obj.parent_tracking_identifier
        else:
            self.action_identifier = action_identifier
            self.subject_identifier = subject_identifier
            self.reference_identifier = reference_identifier
            self.parent_reference_identifier = parent_reference_identifier

        getter = self.action_item_getter(
            self, action_identifier=self.action_identifier,
            subject_identifier=self.subject_identifier,
            reference_identifier=self.reference_identifier,
            parent_reference_identifier=self.parent_reference_identifier,
            allow_create=True)
        self.action_item_obj = getter.model_obj

        if not self.action_identifier:
            self.action_identifier = self.action_item_obj.action_identifier

        if reference_model_obj:
            self.close_and_create_next()

    def __repr__(self):
        return f'{self.__class__.__name__}({self.name})'

    def __str__(self):
        return self.name

    @classmethod
    def action_item_model_cls(cls):
        return cls.action_item_getter.model_cls()

    @classmethod
    def reference_model_cls(cls):
        return django_apps.get_model(cls.reference_model)

    @classmethod
    def parent_reference_model_cls(cls):
        if cls.parent_reference_model_fk_attr:
            fk = getattr(cls.reference_model_cls(),
                         cls.parent_reference_model_fk_attr)
            return fk.field.related_model
        return None

    @classmethod
    def action_registered_or_raise(cls):
        """Raises if this is not a registered action class.
        """
        registered_cls = site_action_items.get(cls.name)
        if registered_cls is not cls:
            raise ActionError(
                f'Inconsistent name or class. Got {registered_cls} for {cls.name}.')
        return True

    @classmethod
    def as_dict(cls):
        """Returns select class attrs as a dictionary.
        """
        try:
            cls.reference_model = cls.reference_model.lower()
        except AttributeError:
            pass
        return dict(
            name=cls.name,
            display_name=cls.display_name,
            model=cls.reference_model,
            show_on_dashboard=(
                True if cls.show_on_dashboard is None else cls.show_on_dashboard),
            show_link_to_changelist=(
                True if cls.show_link_to_changelist is None else cls.show_link_to_changelist),
            create_by_user=True if cls.create_by_user is None else cls.create_by_user,
            create_by_action=True if cls.create_by_action is None else cls.create_by_action,
            instructions=cls.instructions)

    @classmethod
    def action_type(cls):
        """Returns a model instance of ActionType.

        Gets or creates the model instance on first pass.

        If model instance exists, updates.
        """
        action_type_model_cls = django_apps.get_model(
            cls.action_type_model)
        try:
            action_type = action_type_model_cls.objects.get(
                name=cls.name)
        except ObjectDoesNotExist:
            action_type = action_type_model_cls.objects.create(
                **cls.as_dict())
        else:
            if not cls._updated_action_type:
                for attr, value in cls.as_dict().items():
                    if attr != 'name':
                        setattr(action_type, attr, value)
                action_type.save()
        cls._updated_action_type = True
        return action_type

    def get_next_actions(self):
        """Returns a list of action classes to be created
        again by this model if the first has been closed on post_save.
        """
        return self.next_actions or []

    def close_action_item_on_save(self):
        """Returns True if action item for \'action_identifier\'
        is to be closed on post_save.
        """
        return True

    def close_and_create_next(self):
        """Attempt to close the action item and
        create new ones, if required.
        """

        status = CLOSED if self.close_action_item_on_save() else OPEN
        self.action_item_obj.reference_identifier = self.reference_identifier
        self.action_item_obj.status = status
        self.action_item_obj.save()
        if status == CLOSED:
            self.create_next()

    def create_next(self):
        """Creates any next action items if they do not already exist.
        """
        next_actions = self.get_next_actions()
        for action_cls in next_actions:
            action_cls = self.__class__ if action_cls == 'self' else action_cls
            action_type = action_cls.action_type()
            opts = dict(
                reference_identifier=None,
                subject_identifier=self.subject_identifier,
                action_type=action_type,
                parent_action_item=self.action_item_obj,
                reference_model=action_type.model,
                parent_reference_identifier=self.action_item_obj.reference_identifier,
                parent_reference_model=self.action_type().reference_model,
                instructions=self.instructions)
            try:
                self.action_item_model_cls().objects.get(**opts)
            except ObjectDoesNotExist:
                self.action_item_model_cls().objects.create(**opts)

    def append_to_next_if_required(self, next_actions=None,
                                   action_cls=None, required=None):
        """Returns next actions where action_cls is
        appended if required.

        Will not create if the next action item already exists.
        """
        next_actions = next_actions or []
        required = True if required is None else required
        self.delete_if_new(action_cls)
        try:
            self.action_item_model_cls().objects.get(
                subject_identifier=self.subject_identifier,
                parent_reference_identifier=self.reference_identifier,
                reference_model=action_cls.reference_model)
        except ObjectDoesNotExist:
            if required:
                next_actions.append(action_cls)
        return next_actions

    def delete_if_new(self, action_cls=None):
        opts = dict(
            subject_identifier=self.subject_identifier,
            parent_reference_identifier=self.reference_identifier,
            reference_model=action_cls.reference_model,
            status=NEW)
        return self.action_item_model_cls().objects.filter(**opts).delete()

    @classmethod
    def reference_model_url(cls, action_item=None, reference_model_obj=None, **kwargs):
        """Returns a relative add URL with querystring that can
        get back to the subject dashboard on save.
        """
        if cls.parent_reference_model_fk_attr and action_item.parent_reference_model_obj:
            try:
                value = getattr(action_item.parent_object,
                                cls.parent_reference_model_fk_attr)
            except (ObjectDoesNotExist, AttributeError):
                value = action_item.parent_reference_model_obj
            kwargs.update({
                cls.parent_reference_model_fk_attr: str(value.pk)})
        query = unquote(urlencode(kwargs))
        if reference_model_obj:
            path = reference_model_obj.get_absolute_url()
        else:
            path = cls.reference_model_cls()().get_absolute_url()
        return '?'.join([path, query])