<%inherit file="../base.mako" />\
<%block name="title">Password reset - </%block>
<%block name="body_class">layout2</%block>
<h2>Password reset</h2>
<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <p>This user's password has been reset to ${new_password}.</p>
  </div>
</main>
