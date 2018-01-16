# Generated by Django 2.0.1 on 2018-01-16 13:28

from django.db import migrations, models
import django.db.models.deletion
import edc_base.sites.managers


class Migration(migrations.Migration):

    dependencies = [
        ('sites', '0002_alter_domain_unique'),
        ('edc_action_item', '0002_auto_20180109_1117'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='actionitem',
            managers=[
                ('on_site', edc_base.sites.managers.CurrentSiteManager()),
            ],
        ),
        migrations.AddField(
            model_name='actionitem',
            name='site',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, to='sites.Site'),
        ),
        migrations.AddField(
            model_name='historicalactionitem',
            name='site',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='sites.Site'),
        ),
    ]