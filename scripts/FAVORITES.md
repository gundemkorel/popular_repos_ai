Update dashboard to add Favorites lane.

Files:
- app.js (add star toggle on card, Favorites lane, localStorage persistence, "Copy favorites as text" button)
- styles.css (star button styling, favorites lane, copy button)

Requirements:
1. After "# Order" chips, show "Favorites" chip. When clicked, show favorites lane.
2. Each repo card gets a star button in card-top (right side of name area). Click toggles favorite for that full_name.
3. Favorites stored in localStorage key "first-project-favs" as array of full_name strings.
4. If favorites exist, show Favorites lane as its own section. Favorites ordered by user add-order, newest first is fine.
5. Favorites lane has a "Copy favorites as text" button. When clicked, builds a plain text block:
   ```
   # My Favorites (Copied YYYY-MM-DD)
   - owner/name — description
     https://github.com/owner/name
   ```
   Copies to clipboard and shows "Copied" for 2s. If no favorites: "No favorites yet" state.
6. Star button uses ★ unicode or an SVG star icon; filled when favorite, outline when not.
7. When favorites change, re-render to update chip active state? No — just toggle stars visually. But Favorites lane must refresh when favorites change.
8. Keep existing card expand behavior for non-star clicks.
9. Make sure star toggle works on mobile touch.

Important: Favorites are stored in browser localStorage. They are local to the browser profile — not synced to Telegram or other browsers. A "Copy favorites" button exports them as text the user can paste into the chat.

After writing, verify it parses:
  node -e "d=require('fs').readFileSync('/Users/korelgundem/Desktop/first-project/dashboard/app.js','utf8');new Function(d);console.log('app.js ok')"
  node -e "d=require('fs').readFileSync('/Users/korelgundem/Desktop/first-project/dashboard/styles.css','utf8');console.log('css ok len',d.length)"
