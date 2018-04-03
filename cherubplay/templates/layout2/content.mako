<%inherit file="base.mako" />\
<%block name="title">${title} - </%block>
<h2>${title}</h2>
<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    ${content|n}
  </div>
</main>
