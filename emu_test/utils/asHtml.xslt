<?xml version="1.0" encoding="UTF-8" ?>
<!-- A very basic self contained html page that displays the tests. -->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="testsuite">
        <html>
            <head>
                <title> Test Results For
                    <xsl:value-of select="@name"/>
                </title>
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet" />
                <style>
body {
        background: #ffffff;
        color: #000000;
        font-size: 13px;
        font-family: Verdana, Arial, Helvetica, sans-serif;
        font-size: 12px;
        text-align: justify;
}
h1 { font-size: 30px; }
h2 { font-size: 20px; }
h3 { font-size: 16px; }
h4 { font-size: 12px; font-style: bold;}
dt { font-style: italic; }

pre {
        border: solid #0000ff 1px;
        color: #000000;
        white-space: pre-wrap;       /* css-3 */
        white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
        white-space: -pre-wrap;      /* Opera 4-6 */
        white-space: -o-pre-wrap;    /* Opera 7 */
        word-wrap: break-word;       /* Internet Explorer 5.5+ */
        background-color: #ffffd0;
        padding-left: 10px;
        padding-right: 10px;
        padding-top: 10px;
        padding-bottom: 10px;
        margin-top: 0px;
        text-align: left;
        margin-left: auto;
        margin-right: auto;
        font-family:    Courier,Monospace, Courier, MS Courier New, Prestige, Everson Mono;
        font-style: normal;
        font-size: 14;
}


/* Scapy default color theme */

span.prompt { color: #0000ff; font-weight: bold; }
span.not_printable { color: #a0a0a0; }
span.layer_name { color: #ff0000; font-weight: bold; }
span.field_name { color: #0000ff; }
span.field_value { color: #ff00ff; }
span.emph_field_name { color: #0000ff; font-weight: bold; text-decoration: underline }
span.emph_field_value { color: #ff00ff; font-weight: bold; text-decoration: underline }
span.packetlist_name { color: #ff0000; font-weight: bold; }
span.packetlist_proto { color: #0000ff; }
span.packetlist_value { color: #ff00ff; }
span.fail { color: #ff0000; font-weight: bold; }
span.success { color: #0000ff; font-weight: bold; }
span.even { color: #000000; font-weight: bold; }
span.odd { color: #000000; }
span.opening { color: #00ffff; }
span.active { color: #000000; }
span.closed { color: #808080; }


.num    { color:#2928ff; }
.esc    { color:#830000; }
.str    { color:#c00000; }
.dstr   { color:#818100; }
.slc    { color:#838183; font-style:italic; }
.com    { color:#838183; font-style:italic; }
.dir    { color:#ff0000; }
.sym    { color:#000000; }
.line   { color:#555555; }
.blue   { color:#0000ff; font-style:italic; }
.kwa    { color:#000000; font-weight:bold; }
.kwb    { color:#00a000; }
.kwc    { color:#00a000; }

.pass {background-color: #ffffff; color: #008900;}
.fail {background-color: #ffffff; color: #bd2121;}
.error {background-color: #ffffff; color: #720808;}

li.passed {color: #002000;}
li.failed {color: #200000;}
span.comment { color:#000000; font-style: italic;}

span.crc {
            font-family: monospace;
            font-size: 12px;
            font-weight: normal;
            margin-top: 10px;
            background-color: #ccccff;
}

span.buttonskip {
            font-family: monospace;
            margin-top: 10px;
            border: 1px solid black;
            padding: 0 2px;
            margin-right: 2px;
}
span.buttonpassed {
            font-family: monospace;
            margin-top: 10px;
            background-color: #aaffaa;
            border: 1px solid black;
            padding: 0 2px;
            margin-right: 2px;
}
span.buttonfailed {
        font-family: monospace;
        margin-top: 10px;
        background-color: #ffaaaa;
        border: 1px solid black;
        padding: 0 2px;
        margin-right: 2px;
        cursor: pointer;
}
span.buttonerror {
        font-family: monospace;
        margin-top: 10px;
        background-color: #dd5d5d;
        border: 1px solid black;
        padding: 0 2px;
        margin-right: 2px;
        cursor: pointer;
}

/* New properties used in the containers that display the attachments */

.embedding {
    background-color: #fff;
    overflow: auto;
    margin-left: 17px;
    margin-bottom: 10px;
    border: solid 1px #ccc;
    display: inline-block;
    float: left;
}

.text-box {
    text-align: left;
    margin: 0 1px;
    font-size: 13px;
    overflow-x: auto;
    line-height: 1.42857143;
    color: #bd0a2b;
    white-space: pre-wrap;
    word-wrap: break-word;
    background-color: #fff0f0;
    border: 0px solid #ccc;
    display: inline-block;
}

ul.attachments {
    list-style-type: none; /* Remove bullets */
    padding: 0; /* Remove padding */
    margin: 0; /* Remove margins */
    margin-top: 3px;
}

li.attachment {
    margin-left: 25px;
    padding: 1px;
    font-size: 13px;
    line-height: 1.42857143;
    color: #333;
}

li.attachment::marker {
    content: "\f0c6   ";
    font-family: FontAwesome;
}

a.header {
    margin-left: 5px;
    color: #004a6a;
    font-size: 13px;
    line-height: 1.42857143;
}

li.collapsable {
    margin-left: 10px;
    padding: 1px;
    font-size: 13px;
    line-height: 1.42857143;
    color: #333;
    cursor: pointer;
}

.image-box {
    height:600px;
}

.img {
    max-height: 600px;
    display: inline-block;
    visibility: visible;
}

                </style>
                <script language="JavaScript">

function toggle(container) {
    var icon = container.getElementsByClassName("icon")[0];
    var contents = container.getElementsByClassName("contents")[0];
    var image = container.getElementsByClassName("img")[0];
    var base64 = container.getElementsByClassName("base64enc")[0];
    // toggling icon
    icon.classList.toggle('fa-angle-right');
    icon.classList.toggle('fa-angle-down');
    // toggling contents
    if (contents.style.display === "none") {
        image.setAttribute('src', base64.innerHTML);
        image.style.display = "block";
        contents.style.display = "block";
    } else {
        image.removeAttribute('src');
        image.style.display = "none";
        contents.style.display = "none";
    }
}

function make_visible(elt) { elt.style.visibility='visible'; elt.style.position='relative';
}

function make_hidden(elt) { elt.style.visibility='hidden'; elt.style.position='absolute';
}

function hide(id) {
    make_hidden(document.getElementById(id+'-'))
    make_visible(document.getElementById(id+'+'))
    make_hidden(document.getElementById(id))
}

function show(id) {
    make_visible(document.getElementById(id+'-'))
    make_hidden(document.getElementById(id+'+'))
    make_visible(document.getElementById(id))
}

function goto_id(id) {
    document.body.scrollTop = document.getElementById(id).offsetTop;
}

                </script>
            </head>
            <body>
                <h1>Test Results for:
                    <xsl:value-of select="@name"/>
                </h1>
                <p> TOTAL=
                    <xsl:value-of select="@tests"/>
, <font class="pass"> PASSED </font>=
                    <xsl:value-of select="@tests - @failures - @errors - @skipped"/>
, <font class="fail"> FAILED </font>=
                    <xsl:value-of select="@failures"/>
, <font class="error"> ERRORS </font>=
                    <xsl:value-of select="@errors"/>
, SKIPPED=
                    <xsl:value-of select="@skipped"/>
                </p>
                <!-- SUMMARY SQUARES SECTION -->
                <xsl:for-each select="testcase">
                    <xsl:variable name="id" select="position()"/>
                    <xsl:variable name="fid" select=" format-number($id, '000')"/>
                    <xsl:variable name="buttonclass">
                        <xsl:choose>
                            <xsl:when test="failure">buttonfailed</xsl:when>
                            <xsl:when test="error">buttonerror</xsl:when>
                            <xsl:when test="skipped">buttonskip</xsl:when>
                            <xsl:otherwise>buttonpassed</xsl:otherwise>
                        </xsl:choose>
                    </xsl:variable>
                    <span class="{$buttonclass}" onClick="goto_id('tst{$id}l')">
                        <xsl:value-of select="$fid"/>
                    </span>
                </xsl:for-each>
                <!-- TESTS SECTION -->
                <h2>tests</h2>
                <xsl:for-each select="testcase">
                    <xsl:variable name="id" select="position()"/>
                    <xsl:variable name="fid" select="format-number($id, '000')"/>
                    <xsl:choose>
                        <xsl:when test="failure or error">
                            <xsl:variable name="buttonclass">
                                <xsl:if test="failure">buttonfailed</xsl:if>
                                <xsl:if test="error">buttonerror</xsl:if>
                            </xsl:variable>
                            <li class="failed" id="tst{$id}l">
                                <span id="tst{$id}+" class="{$buttonclass}" onClick="show('tst{$id}')">
                                +
                                    <xsl:value-of select="$fid"/>
                                +</span>
                                <span id="tst{$id}-" class="{$buttonclass}" onClick="hide('tst{$id}')" style="position: absolute; visibility: hidden;">
                                -
                                    <xsl:value-of select="$fid"/>
                                -</span>&#160;
                                <xsl:value-of select="@classname"/>
.
                                <xsl:value-of select="@name"/>
                                <div style="clear: both;"></div>
                                <span id="tst{$id}" style="position: absolute; visibility: hidden;">
                                    <div class="embedding">
                                        <pre class="text-box">
                                            <xsl:value-of select="."/>
                                        </pre>
                                        <ul class="attachments">
                                            <!--xsl:for-each select="hierarchies/*">
                                                <xsl:variable name="path" select="@path"/>
                                                <li class="attachment">
                                                    <a href="{$path}" target="_blank"><xsl:value-of select="@name"/></a>
                                                </li>
                                            </xsl:for-each-->
                                            <xsl:for-each select="screenshots/*">
                                                <li class="collapsable" onclick="toggle(this);">
                                                    <i class="fa fa-sharp fa-angle-right icon">&#160;</i>
                                                    <a class="header"><xsl:value-of select="@name"/></a>
                                                    <div class="contents" style="display:none">
                                                        <div class="base64enc" hidden="hidden" style="display:none">data:image/png;base64,<xsl:value-of select="@base64"/></div>
                                                        <div class="image-box">
                                                            <img class="img" style="display:none"></img>
                                                        </div>
                                                    </div>
                                                </li>
                                            </xsl:for-each>
                                        </ul>
                                    </div>
                                </span>
                                <div style="clear: both;"></div>
                            </li>
                        </xsl:when>
                        <xsl:when test="skipped">
                            <li class="skipped" id="tst{$id}l">
                                <span id="tst{$id}" class="buttonskip" >&#160;
                                    <xsl:value-of select="$fid"/>&#160;
                                </span>
                                        &#160;
                                <xsl:value-of select="@classname"/>
.
                                <xsl:value-of select="@name"/>
                                <span class="comment skipped" id="tst{$id}" style="position: absolute; visibility: hidden;">
                                    <pre>
                                        <xsl:value-of select="."/>
                                    </pre>
                                </span>
                            </li>
                        </xsl:when>
                        <xsl:otherwise>
                            <li class="passed" id="tst{$id}l">
                                <span id="tst{$id}+" class="buttonpassed">&#160;
                                    <xsl:value-of select="$fid"/>&#160;
                                </span>&#160;
                                <xsl:value-of select="@classname"/>
.
                                <xsl:value-of select="@name"/>
                                <span class="comment passed" id="tst{$id}" style="position: absolute; visibility: hidden;">
                                    <pre>
                                        <xsl:value-of select="."/>
                                    </pre>
                                </span>
                            </li>
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:for-each>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
