/**
 * Expand the first level of each top-level RTD sidebar section on page load.
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

        if (item.classList.contains('current') || item.classList.contains('on')) {
            continue;
        }

        const expandControl = item.querySelector(
            ':scope > a > button.toctree-expand, :scope > a > span.toctree-expand'
        );

        if (expandControl) {
            expandControl.click();
        } else {
            item.classList.add('ewms-force-open');
            item.setAttribute('aria-expanded', 'true');
            childList.setAttribute('aria-expanded', 'true');
            childList.style.display = 'block';
        }
    }
});
