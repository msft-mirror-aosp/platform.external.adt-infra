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
        word-wrap: break-word;       /* Internet Explorer 5.5 */
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
.fail {background-color: #ffffff; color: #b50000;}

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
}
span.buttonpassed {
            font-family: monospace;
            margin-top: 10px;
            background-color: #aaffaa;
}
span.buttonfailed {
        font-family: monospace;
        margin-top: 10px;
        background-color: #ffaaaa;
}
                </style>
                <script language="JavaScript">
function make_visible(elt) { elt.style.visibility='visible'; elt.style.position='relative';
}

function make_hidden(elt) { elt.style.visibility='hidden'; elt.style.position='absolute';
}

function hide(id) {
    make_hidden(document.getElementById(id'-'))
    make_visible(document.getElementById(id''))
    make_hidden(document.getElementById(id))
}

function show(id) {
    make_visible(document.getElementById(id'-'))
    make_hidden(document.getElementById(id''))
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
, <font class="fail"> ERRORS </font>=
                    <xsl:value-of select="@errors"/>
, SKIPPED=
                    <xsl:value-of select="@skipped"/>
                </p>
                <xsl:for-each select="testcase">
                    <xsl:variable name="id" select="position()"/>
                    <xsl:variable name="fid" select=" format-number($id, '0000')"/>
                    <xsl:choose>
                        <xsl:when test="failure">
                            <span class="buttonfailed" onClick="goto_id('tst{$id}l')">
                                <xsl:value-of select="$fid"/>
                            </span>&#160;
                        </xsl:when>
                        <xsl:when test="error">
                            <span class="buttonfailed" onClick="goto_id('tst{$id}l')">
                                <xsl:value-of select="$fid"/>
                            </span>&#160;
                        </xsl:when>
                        <xsl:when test="skipped">
                            <span class="buttonskip" onClick="goto_id('tst{$id}l')">
                                <xsl:value-of select="$fid"/>
                            </span>&#160;
                        </xsl:when>
                        <xsl:otherwise>
                            <span class="buttonpassed" onClick="goto_id('tst{$id}l')">
                                <xsl:value-of select="$fid"/>
                            </span>&#160;
                        </xsl:otherwise>
                    </xsl:choose>
                </xsl:for-each>
                <h2>tests</h2>
                <xsl:for-each select="testcase">
                    <xsl:variable name="id" select="position()"/>
                    <xsl:variable name="fid" select="format-number($id, '0000')"/>
                    <xsl:choose>
                        <xsl:when test="failure">
                            <li class="failed" id="tst{$id}l">
                                <span id="tst{$id}" class="buttonfailed" onClick="show('tst{$id}')">
                                
                                    <xsl:value-of select="$fid"/>
                                </span>
                                <span id="tst{$id}-" class="buttonfailed" onClick="hide('tst{$id}')" style="POSITION: absolute; VISIBILITY: hidden;">
                                -
                                    <xsl:value-of select="$fid"/>
                                -</span>
                                        &#160;
                                <xsl:value-of select="@classname"/>
.
                                <xsl:value-of select="@name"/>
                                <span class="comment failed" id="tst{$id}" style="POSITION: absolute; VISIBILITY: hidden;">
                                    <pre>
                                        <xsl:value-of select="."/>
                                    </pre>
                                </span>
                            </li>
                        </xsl:when>
                        <xsl:when test="skipped">
                            <li class="skipped" id="tst{$id}l">
                                <span id="tst{$id}" class="buttonskip" >&#160;
                                    <xsl:value-of select="$fid"/>&#160;
                                </span>
                                        &#160;&#160;
                                <xsl:value-of select="@classname"/>
.
                                <xsl:value-of select="@name"/>
                                <span class="comment skipped" id="tst{$id}" style="POSITION: absolute; VISIBILITY: hidden;">
                                    <pre>
                                        <xsl:value-of select="."/>
                                    </pre>
                                </span>
                            </li>
                        </xsl:when>
                        <xsl:when test="error">
                            <li class="error" id="tst{$id}l">
                                <span id="tst{$id}" class="buttonerror" onClick="show('tst{$id}')">
                                
                                    <xsl:value-of select="$fid"/>
                                </span>
                                <span id="tst{$id}-" class="buttonerror" onClick="hide('tst{$id}')" style="POSITION: absolute; VISIBILITY: hidden;">
                                -
                                    <xsl:value-of select="$fid"/>
                                -</span>
                                        &#160;
                                <xsl:value-of select="@classname"/>
.
                                <xsl:value-of select="@name"/>
                                <span class="comment error" id="tst{$id}" style="POSITION: absolute; VISIBILITY: hidden;">
                                    <pre>
                                        <xsl:value-of select="."/>
                                    </pre>
                                </span>
                            </li>
                        </xsl:when>
                        <xsl:otherwise>
                            <li class="passed" id="tst{$id}l">
                                <span id="tst{$id}" class="buttonpassed">&#160;
                                    <xsl:value-of select="$fid"/>&#160;
                                </span>&#160;&#160;
                                <xsl:value-of select="@classname"/>
.
                                <xsl:value-of select="@name"/>
                                <span class="comment passed" id="tst{$id}" style="POSITION: absolute; VISIBILITY: hidden;">
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
