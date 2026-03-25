/**
 * Force the first level of each top-level RTD sidebar section open.
 *
 * This keeps the EWMS navigation tree more consistently open across pages
 * without modifying the Sphinx RTD theme templates themselves.
 */
document.addEventListener('DOMContentLoaded', () => {
    const menu = document.querySelector('.wy-menu-vertical');
    if (!menu) {
        return;
    }

    for (const item of menu.querySelectorAll('li.toctree-l1')) {
        const childList = item.querySelector(':scope > ul');
        if (!childList) {
            continue;
        }

        if (!item.classList.contains('current') && !item.classList.contains('on')) {
            item.classList.add('ewms-force-open');
        }

        childList.style.display = 'block';
    }
});
