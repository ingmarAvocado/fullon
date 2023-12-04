<%
import arrow
%>

<div class="container">
    <p>

    <h6><a href="detail?tempkey=${bot.bot_id}">Bot Details</a></h6>
        <table id="fullon" class="display compact  table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    <th>Name</th>
                    <th>Live</th>
                    <th>market</th>
                    <th>Since</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>${bot_view.name}</td>

                    <td>${bot.live}</td>
                    <td>${bot.market}</td>
                    <td>${bot.timestamp}</td>
                </tr>               
            </tbody>
        </table>
    
        <p></p>
    <h6>Bot Log</h6>
        <table id="fullon" class="display compact  table-striped table-bordered" style="width:100%"> 
            <thead>
                <tr>
                    <th>Log</th>
                    <th>Date</th>
                </tr>
            </thead>
            <tbody>
                %for log in logs:
                <tr>
                    <td>
                        <table id="fullon" class="display compact  " style="width:100%">
                        % for message in log.message:
                        <tr>
                            <td>${message.name}</td><td>${message.value}</td>
                        </tr>
                        % endfor  
                        </table>
                    </td>
                    <td>${log.timestamp}</td>
                </tr>
                %endfor:                              
            </tbody>
        </table>   
    <p>    
</div>

