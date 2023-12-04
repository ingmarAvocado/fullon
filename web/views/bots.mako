
 <div class="container">
        <p></p>
    <h6>Current Active Bots</h6>

        <script>
                $(document).ready(function() {
                    $('#botlist').DataTable( {
                        "paging":   false,
                        "order": [[ 0, "desc" ]],
                        "ordering": false,
                        "info":     false,
                        "searching": false,
                        "scrollX": false,
                        "ajax": {
                            "url": "/get_bots",
                            "dataSrc": "data"
                        }
                    } );
                } );
       </script>
        <table id="botlist" class="display table-striped table-bordered" style="width:100%"> 
            <thead>                
                <tr>
                    <th>Name</th>
                    <th>Live</th>
                    <th>Strategy</th>
                    <th>Symbol</th>
                    <th>Exchange</th>
                    <th>Market </th>                    
                    <th>Tick</th>
                    <th>Size</th>
                    <th>Price</th>
                    <th>ROI</th>
                    <th>%</th>
                    <th>Last (UTC)</th>
                </tr>
            </thead>
            <tbody>

            </tbody>
        </table>
    <p>
</div>

<script language="javascript" type="text/javascript">

var timeout = setInterval(reloadChat, 5000);    
function reloadChat () {
     $('#botlist').DataTable().ajax.reload();;
}
</script>