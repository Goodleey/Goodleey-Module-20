from django.db.models.signals import m2m_changed, post_delete, post_save
from django.dispatch import receiver
from django.core.cache import cache
from tasks.models import TodoItem, Category, Priority
from collections import Counter


@receiver(m2m_changed, sender=TodoItem.category.through)
def task_cats_added(sender, instance, action, model, **kwargs):

    # sender - through
    # instance - TodoItem object
    # model - Category

    if action != "post_add":
        return

    cache.clear()

    for cat in instance.category.all():
        slug = cat.slug

        new_count = 0
        for task in TodoItem.objects.all():
            new_count += task.category.filter(slug=slug).count()

        Category.objects.filter(slug=slug).update(todos_count=new_count)


def reset_counts():
    cat_counter = Counter()
    for cat in Category.objects.all():
        cat_counter[cat.slug] = 0
    for t in TodoItem.objects.all():        
        for cat in Category.objects.all():
            cat_counter[cat.slug] += t.category.filter(slug=cat.slug).count()

    for slug, new_count in cat_counter.items():
        Category.objects.filter(slug=slug).update(todos_count=new_count)


@receiver(m2m_changed, sender=TodoItem.category.through)
def task_cats_removed(sender, instance, action, model, **kwargs):
    if action != "post_remove":
        return

    cache.clear()
    reset_counts()


def reset_priority_counts():
    pri_counter = {1: 0, 2: 0, 3: 0}
    
    for t in TodoItem.objects.all():        
        pri_counter[t.priority.priority] += 1

    for pri, new_count in pri_counter.items():
        Priority.objects.filter(priority=pri).update(count=new_count)


@receiver(post_save, sender=TodoItem)
def task_saved(sender, instance, created, **kwargs):    
    cache.clear()
    if created:
        instance.priority.count += 1
        instance.priority.save()
    else:
        reset_priority_counts()


@receiver(post_delete, sender=TodoItem)
def task_removed(sender, instance, **kwargs):    
    cache.clear()
    reset_counts()
    instance.priority.count = max(0, instance.priority.count-1)
    instance.priority.save()