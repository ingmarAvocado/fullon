<%
import arrow
%>

 <div class="container">
        <p></p>
    <h6>Current Active Bots</h6>

        <script>
                $(document).ready(function() {
                    $('#fullon').DataTable( {
                        "paging":   false,
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
        <table id="fullon" class="display compact   table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    
                    <th colspan="9" style="text-align: center; vertical-align: middle;">Bot Details</th>
                    <th colspan="5" style="text-align: center; vertical-align: middle;">Unrealised Activity<th>
                </tr>
                <tr>
                    <th>Symbol</th>
                    <th>Live</th>
                    <th>Strategy</th>
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

var timeout = setInterval(reloadChat, 15000);    
function reloadChat () {
     $('#fullon').DataTable().ajax.reload();;
}
</script>
