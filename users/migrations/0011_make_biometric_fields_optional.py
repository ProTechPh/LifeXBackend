# Generated manually to make BiometricData fields optional for lenient OCR

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0010_add_id_scan_fields'),
    ]

    operations = [
        migrations.AlterField(
            model_name='biometricdata',
            name='id_number',
            field=models.CharField(blank=True, default='', help_text='ID number extracted from card', max_length=50),
        ),
        migrations.AlterField(
            model_name='biometricdata',
            name='id_full_name',
            field=models.CharField(blank=True, default='', help_text='Full name as shown on ID', max_length=255),
        ),
        migrations.AlterField(
            model_name='biometricdata',
            name='id_date_of_birth',
            field=models.DateField(blank=True, help_text='Date of birth from ID', null=True),
        ),
        migrations.AlterField(
            model_name='biometricdata',
            name='id_address',
            field=models.TextField(blank=True, default='', help_text='Address from ID'),
        ),
        migrations.AlterField(
            model_name='biometricdata',
            name='id_face_image',
            field=models.ImageField(blank=True, help_text='Face extracted from ID card', null=True, upload_to='id_faces/%Y/%m/%d/'),
        ),
        migrations.AlterField(
            model_name='biometricdata',
            name='id_face_encoding',
            field=models.JSONField(blank=True, help_text='Face encoding from ID card (128-dim array)', null=True),
        ),
    ]
