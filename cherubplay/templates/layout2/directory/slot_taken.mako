<%inherit file="base.mako" />\
<%block name="heading">Error</%block>
<% from cherubplay.models import Tag %>
    <p>Sorry, someone else has already chosen that slot.</p>
    <p>Please <a href="javascript:history.back(1);">go back</a> and choose another.</p>
