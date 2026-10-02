document.querySelectorAll('.product-card, .category-card').forEach((el, i) => {
    el.style.opacity = 0;
    el.style.transform = 'translateY(10px)';
    setTimeout(() => {
        el.style.transition = 'all .3s ease';
        el.style.opacity = 1;
        el.style.transform = 'translateY(0)';
    }, i * 40);
});