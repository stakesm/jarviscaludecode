<script lang="ts">
    const currentYear = new Date().getFullYear()
</script>

<footer id="footer">
    <p>© {currentYear} Jarvis</p>
</footer>

<style lang="scss">
    #footer {
        text-align: center;
        color: #6c6e71;
        font-size: 13px;
        font-weight: normal;
        line-height: 1.7em;
        margin-top: 15px;

        p {
            margin: 0;
            padding: 0;
        }
    }
</style>
