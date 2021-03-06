from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from edc_constants.constants import OPEN

from .models import ActionItem, ActionItemUpdate


@receiver(post_save, weak=False, dispatch_uid='update_or_create_action_item_on_post_save')
def update_or_create_action_item_on_post_save(sender, instance, raw,
                                              created, update_fields, **kwargs):
    """Updates action item for a model using the ActionModelMixin.

    Instantiates the action class on the model with the model's
    instance.
    """
    if not raw and not update_fields:
        try:
            instance.action_identifier
        except AttributeError:
            pass
        else:
            if ('historical' not in instance._meta.label_lower
                    and not (isinstance(instance, ActionItem) or 
                             isinstance(instance, ActionItemUpdate))):
                instance.action_cls(reference_model_obj=instance)


@receiver(post_delete, weak=False,
          dispatch_uid="action_on_post_delete")
def action_on_post_delete(sender, instance, using, **kwargs):
    """Re-opens an action item when the action's reference
    model is deleted.
    """
    if not isinstance(instance, ActionItem):
        try:
            instance.action_cls
        except AttributeError:
            pass
        else:
            obj = ActionItem.objects.get(
                action_identifier=instance.action_identifier)
            obj.status = OPEN
            obj.reference_identifier = None
            obj.save()
