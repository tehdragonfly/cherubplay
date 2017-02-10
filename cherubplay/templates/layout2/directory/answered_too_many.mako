<%inherit file="base.mako" />\
<%block name="heading">Error</%block>
<% from cherubplay.models import Tag %>
    <p>Sorry, you've answered too many requests recently.</p>
    <p>Please try again later.</p>
