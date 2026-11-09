# SmartCart responsive UI update

- All admin and user templates now inherit the shared `templates/base.html` layout.
- Shared styling is in `static/css/style.css`.
- The navigation collapses into a menu on phone screens.
- Product grids use four columns on wide desktops, two on tablets, and one on phones.
- Forms, tables, order cards, images, and invoice pages have fluid sizing and overflow handling.

The breakpoints are approximately 900px (tablet) and 640px (phone). To customize the theme, edit the CSS variables at the top of `static/css/style.css`.
