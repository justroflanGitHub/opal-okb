
void FUN_0000_2933(void)

{
  int in_BX;
  int iVar1;
  undefined1 *unaff_SI;
  char *unaff_DI;
  undefined2 unaff_ES;
  undefined2 unaff_DS;
  
code_r0x00002933:
  do {
    iVar1 = in_BX + 1;
    if (unaff_SI[iVar1] == '\n') {
      do {
        in_BX = in_BX + 1;
      } while (unaff_DI[in_BX] == ' ');
      if (unaff_DI[in_BX] == '=') {
        do {
          in_BX = in_BX + 1;
        } while (unaff_DI[in_BX] == ' ');
        FUN_0100_1722(unaff_DI + in_BX);
        return;
      }
    }
    else {
      in_BX = iVar1;
      if (unaff_DI[iVar1] == unaff_SI[iVar1]) goto code_r0x00002933;
      unaff_DI = unaff_DI + 1;
    }
    in_BX = -1;
    if ((*unaff_DI == '\0') && (unaff_DI[1] == '\0')) {
      *unaff_SI = 0;
      return;
    }
  } while( true );
}

