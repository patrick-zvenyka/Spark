def question_stats(queryset):
    return {
        "total": queryset.count(),
        "open": queryset.filter(status="open").count(),
        "answered": queryset.filter(status="answered").count(),
    }
