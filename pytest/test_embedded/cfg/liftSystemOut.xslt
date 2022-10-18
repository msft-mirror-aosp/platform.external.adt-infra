<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>
    <xsl:strip-space elements="*"/>
    <!-- identity transform -->
    <xsl:template match="@*|node()">
        <xsl:copy>
            <xsl:apply-templates select="@*|node()"/>
        </xsl:copy>
    </xsl:template>
    <xsl:template match="failure">
        <failure>
            <xsl:attribute name="message">
                <xsl:value-of select="."/>
                <xsl:text>&#10;</xsl:text>
                <xsl:value-of select="../system-out"/>
            </xsl:attribute>
        </failure>
    </xsl:template>
    <xsl:template match="error">
        <error>
            <xsl:attribute name="message">
                <xsl:value-of select="."/>
                <xsl:text>&#10;</xsl:text>
                <xsl:value-of select="../system-out"/>
            </xsl:attribute>
        </error>
    </xsl:template>
    <!-- drop output -->
    <xsl:template match="system-out" />
</xsl:stylesheet>