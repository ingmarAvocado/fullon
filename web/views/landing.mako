 <%
import arrow
%>
<div class="container-fluid">
    <div class = "container text-center">
        <picture>
            <source media="(min-width: 750px)" srcset="static/images/logo.png">
            <source media="(min-width: 265px)" srcset="static/images/logosmall.png">
            <img src="default-logo" alt="logo" style="width:auto;">
        </picture>
    </div>
   
    <div class="container">
        <div class="row text-center">
            <div class="col">
                <a href="/accounts">
                    <picture>
                        <source media="(min-width: 750px)" srcset="static/images/ex.png">
                        <source media="(min-width: 265px)" srcset="static/images/exsmall.png">
                        <img src="ex-logo" alt="Accounts" style="width:auto;">
                    </picture>
                    <p>Accounts</p>
                </a>
            </div>

            <div class="col">
                <a href="/bots">
                    <picture>
                        <source media="(min-width: 750px)" srcset="static/images/bot.png">
                        <source media="(min-width: 265px)" srcset="static/images/botsmall.png">
                        <img src="logo-bot" alt="logo" style="width:auto;">
                    </picture>
                    <p>Bots</p>
                </a>
            </div>
        </div>
    </div>


    <script>
            $(document).ready(function() {
                $('#overview').DataTable( {
                    "paging":   false,
                    "ordering": false,
                    "info":     false,
                    "searching": false,
                    "scrollX": false,
                    "ajax": {
                        "url": "/procs",
                        "dataSrc": "data"
                    }
                } );
            } );
   </script>


    <div class="container">
        <h4 class="sub-header">Current status:</h4>
        <div class="table-responsive">
            <table id="overview"  class="display compact   table-striped table-bordered " style="width:100%"> 
                <thead class = "text-center">
                    <tr>
                      <th>System RAM GB</th>
                      <th>Free RAM GB</th>
                      <th>App RAM GB</th>
                      <th>CPU time</th>
                      <th>Process Count</th>
                    </tr>
                </thead>
                <tbody class="text-success text-center">
                    <tr role="row" class="odd"><td>15.37</td><td>3.19</td><td>1.02</td><td>18.1</td><td>15</td></tr>
                </tbody>
            </table>                  
          </div>
          <br>
          <div class="table-responsive">
            <table  class="display   table-striped table-bordered " style="width:100%"> 
              <thead class = "text-center">
                <tr>
                  <th>Type</th>
                  <th>T. Count</th>
                  <th>Message</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody class = "text-center">
              %for status in statuses:
                <tr>
                  <td class="text-success">${status.type}</td>
                  <td class="text-success">${status.count}</td>
                  <td class="text-success">${status.message}</td>
                  <td class="text-success">${arrow.get(status.timestamp).format('YYYY-MM-DD HH:mm:ss')}</td>
                </tr>
              % endfor   
              </tbody>
            </table>                  
        </div>
    </div>

</div>

<script language="javascript" type="text/javascript">

var timeout = setInterval(reloadChat, 15000);    
function reloadChat () {
     $('#overview').DataTable().ajax.reload();;
}
</script>