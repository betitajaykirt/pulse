from django.contrib import admin

from myapp.models import Symptom, MitigationProtocol, DiseaseCategoryThreshold


@admin.register(Symptom)
class SymptomAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'syndromic_group', 'description')
    list_filter = ('syndromic_group',)
    search_fields = ('name', 'code', 'description')
    ordering = ('name',)
    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'syndromic_group', 'description'),
        }),
    )


@admin.register(MitigationProtocol)
class MitigationProtocolAdmin(admin.ModelAdmin):
    list_display = ('disease_label', 'action_text_short', 'priority', 'action_category', 'is_active')
    list_filter = ('disease_label', 'priority', 'action_category', 'is_active')
    search_fields = ('disease_label', 'action_text')
    ordering = ('disease_label', '-priority', 'sort_order')

    @admin.display(description='Action')
    def action_text_short(self, obj):
        return obj.action_text[:80] + ('…' if len(obj.action_text) > 80 else '')


@admin.register(DiseaseCategoryThreshold)
class DiseaseCategoryThresholdAdmin(admin.ModelAdmin):
    list_display = (
        'category_level', 'warning_threshold', 'outbreak_threshold',
        'time_window_days', 'is_active',
    )
    list_editable = ('warning_threshold', 'outbreak_threshold', 'time_window_days', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('category_level',)
    ordering = ('category_level',)